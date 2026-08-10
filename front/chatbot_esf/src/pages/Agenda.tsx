import { useCallback, useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

type AppointmentStatus = 'novo' | 'confirmado' | 'cancelado' | 'atendido'
type StatusFilter = AppointmentStatus | 'todos'

type Appointment = {
  id: number
  patient_name: string
  document_masked: string
  service: string
  professional: string
  appointment_date: string
  appointment_time: string
  status: AppointmentStatus
  created_at: string
}

type AppointmentTotals = Record<AppointmentStatus, number> & { total: number }

type WeekDay = {
  value: string
  weekday: string
  dayMonth: string
}

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const AUTH_STORAGE_KEY = 'esf-agenda-auth'
const DEFAULT_TIME_SLOTS = ['10:00', '14:00']
const WORK_WEEK_LENGTH = 5
const WEEKDAY_LABELS = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']

const STATUS_OPTIONS: Array<{ value: StatusFilter; label: string }> = [
  { value: 'todos', label: 'Todos' },
  { value: 'novo', label: 'Novos' },
  { value: 'confirmado', label: 'Confirmados' },
  { value: 'cancelado', label: 'Cancelados' },
  { value: 'atendido', label: 'Atendidos' },
]

const EDITABLE_STATUS_OPTIONS: Array<{ value: AppointmentStatus; label: string }> = [
  { value: 'novo', label: 'Novo' },
  { value: 'confirmado', label: 'Confirmado' },
  { value: 'cancelado', label: 'Cancelado' },
  { value: 'atendido', label: 'Atendido' },
]

function Agenda() {
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [selectedDate, setSelectedDate] = useState(todayInputValue())
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos')
  const [authToken, setAuthToken] = useState(() => sessionStorage.getItem(AUTH_STORAGE_KEY) ?? '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [selectedAppointmentId, setSelectedAppointmentId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const todayValue = useMemo(() => todayInputValue(), [])
  const weekStart = useMemo(() => startOfWeekInputValue(selectedDate), [selectedDate])
  const weekEnd = useMemo(() => addDaysInputValue(weekStart, WORK_WEEK_LENGTH - 1), [weekStart])
  const weekDays = useMemo(() => buildWeekDays(weekStart), [weekStart])
  const weekRangeLabel = `${formatShortDate(weekStart)} a ${formatShortDate(weekEnd)}`

  const totals = useMemo(() => {
    const initialTotals: AppointmentTotals = {
      total: 0,
      novo: 0,
      confirmado: 0,
      cancelado: 0,
      atendido: 0,
    }

    return appointments.reduce<AppointmentTotals>((summary, appointment) => {
      summary.total += 1
      summary[appointment.status] += 1
      return summary
    }, initialTotals)
  }, [appointments])

  const dayTotals = useMemo(() => {
    const groupedTotals = new Map<string, number>()

    for (const appointment of appointments) {
      groupedTotals.set(appointment.appointment_date, (groupedTotals.get(appointment.appointment_date) ?? 0) + 1)
    }

    return groupedTotals
  }, [appointments])

  const appointmentsBySlot = useMemo(() => {
    const groupedAppointments = new Map<string, Appointment[]>()

    for (const appointment of appointments) {
      const key = appointmentSlotKey(appointment.appointment_date, appointment.appointment_time)
      const currentAppointments = groupedAppointments.get(key) ?? []
      currentAppointments.push(appointment)
      groupedAppointments.set(key, currentAppointments)
    }

    return groupedAppointments
  }, [appointments])

  const timeSlots = useMemo(() => {
    const slots = new Set(DEFAULT_TIME_SLOTS)

    for (const appointment of appointments) {
      slots.add(appointment.appointment_time)
    }

    return Array.from(slots).sort(compareTimes)
  }, [appointments])

  const selectedAppointment = useMemo(() => {
    return appointments.find((appointment) => appointment.id === selectedAppointmentId) ?? null
  }, [appointments, selectedAppointmentId])

  const handleLogout = useCallback(() => {
    sessionStorage.removeItem(AUTH_STORAGE_KEY)
    setAuthToken('')
    setAppointments([])
    setSelectedAppointmentId(null)
  }, [])

  const loadAppointments = useCallback(async () => {
    if (!authToken) {
      return
    }

    setIsLoading(true)
    setError('')

    const params = new URLSearchParams()
    params.set('start_date', weekStart)
    params.set('end_date', weekEnd)

    if (statusFilter !== 'todos') {
      params.set('status', statusFilter)
    }

    const queryString = params.toString()

    try {
      const response = await fetch(`${API_BASE_URL}/api/appointments?${queryString}`, {
        headers: authHeaders(authToken),
      })

      if (response.status === 401) {
        handleLogout()
        throw new Error('Usuário ou senha inválidos.')
      }

      if (!response.ok) {
        throw new Error('Não foi possível carregar os agendamentos.')
      }

      const data = (await response.json()) as Appointment[]
      setAppointments(data)
      setSelectedAppointmentId((currentSelectedId) =>
        data.some((appointment) => appointment.id === currentSelectedId) ? currentSelectedId : null,
      )
    } catch (currentError) {
      setAppointments([])
      setSelectedAppointmentId(null)
      setError(connectionErrorMessage(currentError, 'Erro ao carregar agendamentos.'))
    } finally {
      setIsLoading(false)
    }
  }, [authToken, handleLogout, statusFilter, weekEnd, weekStart])

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void loadAppointments()
    }, 0)

    return () => window.clearTimeout(timeoutId)
  }, [loadAppointments])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmedUsername = username.trim()

    if (!trimmedUsername || !password) {
      setError('Digite usuário e senha para acessar a agenda.')
      return
    }

    const nextAuthToken = `Basic ${btoa(`${trimmedUsername}:${password}`)}`
    setIsAuthenticating(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/agenda/session`, {
        headers: authHeaders(nextAuthToken),
      })

      if (response.status === 401) {
        throw new Error('Usuário ou senha inválidos.')
      }

      if (!response.ok) {
        throw new Error('Não foi possível acessar a agenda.')
      }

      sessionStorage.setItem(AUTH_STORAGE_KEY, nextAuthToken)
      setAuthToken(nextAuthToken)
      setUsername('')
      setPassword('')
    } catch (currentError) {
      setError(connectionErrorMessage(currentError, 'Erro ao acessar a agenda.'))
    } finally {
      setIsAuthenticating(false)
    }
  }

  function handleWeekChange(days: number) {
    setSelectedDate(addDaysInputValue(weekStart, days))
  }

  async function handleStatusChange(appointmentId: number, status: AppointmentStatus) {
    if (!authToken) {
      return
    }

    setUpdatingId(appointmentId)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/appointments/${appointmentId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(authToken),
        },
        body: JSON.stringify({ status }),
      })

      if (response.status === 401) {
        handleLogout()
        throw new Error('Usuário ou senha inválidos.')
      }

      if (!response.ok) {
        throw new Error('Não foi possível atualizar o status.')
      }

      const updatedAppointment = (await response.json()) as Appointment
      const shouldHideUpdatedAppointment = statusFilter !== 'todos' && updatedAppointment.status !== statusFilter
      setAppointments((currentAppointments) => {
        if (shouldHideUpdatedAppointment) {
          return currentAppointments.filter((appointment) => appointment.id !== updatedAppointment.id)
        }

        return currentAppointments.map((appointment) =>
          appointment.id === updatedAppointment.id ? updatedAppointment : appointment,
        )
      })
      if (shouldHideUpdatedAppointment) {
        setSelectedAppointmentId(null)
      }
    } catch (currentError) {
      setError(connectionErrorMessage(currentError, 'Erro ao atualizar status.'))
    } finally {
      setUpdatingId(null)
    }
  }

  async function handleDelete(appointment: Appointment) {
    if (!authToken) {
      return
    }

    const shouldDelete = window.confirm(
      `Excluir o agendamento de ${appointment.patient_name} em ${formatDisplayDate(
        appointment.appointment_date,
      )} às ${appointment.appointment_time}?`,
    )

    if (!shouldDelete) {
      return
    }

    setDeletingId(appointment.id)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/appointments/${appointment.id}`, {
        method: 'DELETE',
        headers: authHeaders(authToken),
      })

      if (response.status === 401) {
        handleLogout()
        throw new Error('Usuário ou senha inválidos.')
      }

      if (!response.ok && response.status !== 404) {
        throw new Error('Não foi possível excluir o agendamento.')
      }

      setAppointments((currentAppointments) =>
        currentAppointments.filter((currentAppointment) => currentAppointment.id !== appointment.id),
      )
      setSelectedAppointmentId(null)
    } catch (currentError) {
      setError(connectionErrorMessage(currentError, 'Erro ao excluir agendamento.'))
    } finally {
      setDeletingId(null)
    }
  }

  if (!authToken) {
    return (
      <main className="agenda-page agenda-login-page">
        <section className="agenda-login-shell" aria-label="Acesso à agenda">
          <span className="agenda-eyebrow">ESF São Carlos/Urlândia</span>
          <h1>Agenda da unidade</h1>

          <form className="agenda-login-form" onSubmit={handleLogin}>
            <label>
              Usuário
              <input
                type="text"
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
              />
            </label>

            <label>
              Senha
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>

            {error && <p className="agenda-error">{error}</p>}

            <button className="agenda-primary-button" type="submit" disabled={isAuthenticating}>
              {isAuthenticating ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </section>
      </main>
    )
  }

  return (
    <main className="agenda-page">
      <section className="agenda-shell" aria-label="Agenda da unidade">
        <header className="agenda-header">
          <div className="agenda-brand">
            <div className="agenda-brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M8 2v4M16 2v4M3 10h18" />
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <path d="m9 16 2 2 4-4" />
              </svg>
            </div>
            <div className="agenda-brand-text">
              <h1>Agendamentos</h1>
              <p>Unidade de Saúde - Painel da recepção</p>
            </div>
          </div>

          <div className="agenda-controls" aria-label="Filtros da agenda">
            <label className="agenda-field">
              <svg className="agenda-control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
              <span className="sr-only">Semana</span>
            <input
              type="date"
              value={selectedDate}
              onChange={(event) => {
                if (event.target.value) {
                  setSelectedDate(event.target.value)
                }
              }}
            />
            </label>

            <label className="agenda-field">
              <svg className="agenda-control-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
              </svg>
              <span className="sr-only">Status</span>
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
              {STATUS_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            </label>

            <button
              className="agenda-secondary-button agenda-icon-button"
              type="button"
              title="Semana anterior"
              aria-label="Semana anterior"
              onClick={() => handleWeekChange(-7)}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </button>
            <button className="agenda-secondary-button" type="button" onClick={() => setSelectedDate(todayInputValue())}>
              Hoje
            </button>
            <button
              className="agenda-secondary-button agenda-icon-button"
              type="button"
              title="Próxima semana"
              aria-label="Próxima semana"
              onClick={() => handleWeekChange(7)}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m9 18 6-6-6-6" />
              </svg>
            </button>
            <button className="agenda-primary-button" type="button" onClick={() => void loadAppointments()}>
              <svg className="agenda-button-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
              </svg>
              Atualizar
            </button>

            <button className="agenda-secondary-button" type="button" onClick={handleLogout}>
              Sair
            </button>
          </div>
        </header>

        <section className="agenda-summary" aria-label="Resumo">
          <div className="agenda-stat-total">
            <span>
              <i aria-hidden="true" />
              Total da semana
            </span>
            <strong>{totals.total}</strong>
          </div>
          <div className="agenda-stat-new">
            <span>
              <i aria-hidden="true" />
              Novos
            </span>
            <strong>{totals.novo}</strong>
          </div>
          <div className="agenda-stat-confirmed">
            <span>
              <i aria-hidden="true" />
              Confirmados
            </span>
            <strong>{totals.confirmado}</strong>
          </div>
          <div className="agenda-stat-done">
            <span>
              <i aria-hidden="true" />
              Atendidos
            </span>
            <strong>{totals.atendido}</strong>
          </div>
        </section>

        {error && <p className="agenda-error">{error}</p>}

        <section className="agenda-week-board" aria-label="Calendário semanal de agendamentos">
          <div className="agenda-week-board-header">
            <div>
              <h2>
                Calendário semanal
                <span>{weekRangeLabel} · {appointmentCountLabel(totals.total)}</span>
              </h2>
            </div>
            <div className="agenda-legend" aria-label="Legenda">
              <span>
                <i className="agenda-legend-new" aria-hidden="true" />
                Novo
              </span>
              <span>
                <i className="agenda-legend-confirmed" aria-hidden="true" />
                Confirmado
              </span>
              <span>
                <i className="agenda-legend-canceled" aria-hidden="true" />
                Cancelado
              </span>
              <span>
                <i className="agenda-legend-done" aria-hidden="true" />
                Atendido
              </span>
              <span>
                <i className="agenda-legend-closed" aria-hidden="true" />
                Sem atendimento
              </span>
            </div>
          </div>

          <div className="agenda-week-scroll">
            <table className="agenda-week-table">
              <thead>
                <tr>
                  <th scope="col">Horário</th>
                  {weekDays.map((day) => {
                    const currentDayTotal = dayTotals.get(day.value) ?? 0

                    return (
                      <th className={day.value === todayValue ? 'is-today' : undefined} scope="col" key={day.value}>
                        <span>{day.weekday}</span>
                        <strong>{day.dayMonth}</strong>
                        <em className={currentDayTotal > 0 ? 'has-appointments' : undefined}>
                          {currentDayTotal} agend.
                        </em>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td className="agenda-week-loading" colSpan={weekDays.length + 1}>
                      Carregando agendamentos...
                    </td>
                  </tr>
                ) : (
                  timeSlots.map((timeSlot) => (
                    <tr key={timeSlot}>
                      <th scope="row">
                        <strong>{timeSlot}</strong>
                        <span>{slotPeriodLabel(timeSlot)}</span>
                      </th>
                      {weekDays.map((day) => {
                        const slotAppointments =
                          appointmentsBySlot.get(appointmentSlotKey(day.value, timeSlot)) ?? []
                        const isUnavailable = slotAppointments.length === 0 && isUnavailableSlot(day.value, timeSlot)

                        return (
                          <td
                            className={`agenda-slot-cell${isUnavailable ? ' agenda-slot-cell-unavailable' : ''}`}
                            key={day.value}
                          >
                            <div className="agenda-slot-content">
                              {slotAppointments.length === 0 ? (
                                isUnavailable ? (
                                  <span className="agenda-slot-closed">Sem atendimento</span>
                                ) : (
                                  <span className="agenda-slot-empty">
                                    <svg
                                      viewBox="0 0 24 24"
                                      fill="none"
                                      stroke="currentColor"
                                      strokeWidth="2"
                                      aria-hidden="true"
                                    >
                                      <path d="M12 5v14M5 12h14" />
                                    </svg>
                                    Livre
                                  </span>
                                )
                              ) : (
                                slotAppointments.map((appointment) => (
                                  <button
                                    className={`agenda-slot-appointment agenda-slot-appointment-${appointment.status}`}
                                    key={appointment.id}
                                    type="button"
                                    onClick={() => setSelectedAppointmentId(appointment.id)}
                                  >
                                    <span className="agenda-slot-main">
                                      <strong>{appointment.patient_name}</strong>
                                      <span>{appointment.service}</span>
                                    </span>
                                    <span className={`agenda-slot-status agenda-slot-status-${appointment.status}`}>
                                      {statusLabel(appointment.status)}
                                    </span>
                                  </button>
                                ))
                              )}
                            </div>
                          </td>
                        )
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {selectedAppointment && (
          <div
            className="agenda-detail-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) {
                setSelectedAppointmentId(null)
              }
            }}
          >
            <section
              className="agenda-detail-modal"
              role="dialog"
              aria-modal="true"
              aria-label={`Detalhes do agendamento de ${selectedAppointment.patient_name}`}
            >
              <header className="agenda-detail-header">
                <div>
                  <span>{selectedAppointment.appointment_time}</span>
                  <h2>{selectedAppointment.patient_name}</h2>
                </div>
                <button
                  className="agenda-detail-close"
                  type="button"
                  aria-label="Fechar detalhes"
                  onClick={() => setSelectedAppointmentId(null)}
                >
                  ×
                </button>
              </header>

              <dl className="agenda-detail-list">
                <div>
                  <dt>Data</dt>
                  <dd>{formatDisplayDate(selectedAppointment.appointment_date)}</dd>
                </div>
                <div>
                  <dt>Documento</dt>
                  <dd>{selectedAppointment.document_masked}</dd>
                </div>
                <div>
                  <dt>Serviço</dt>
                  <dd>{selectedAppointment.service}</dd>
                </div>
                <div>
                  <dt>Profissional</dt>
                  <dd>{selectedAppointment.professional}</dd>
                </div>
              </dl>

              <div className="agenda-detail-actions">
                <label className={`agenda-status agenda-status-${selectedAppointment.status}`}>
                  Status
                  <select
                    value={selectedAppointment.status}
                    disabled={updatingId === selectedAppointment.id || deletingId === selectedAppointment.id}
                    onChange={(event) =>
                      void handleStatusChange(selectedAppointment.id, event.target.value as AppointmentStatus)
                    }
                  >
                    {EDITABLE_STATUS_OPTIONS.map((option) => (
                      <option value={option.value} key={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <button
                  className="agenda-danger-button"
                  type="button"
                  disabled={deletingId === selectedAppointment.id || updatingId === selectedAppointment.id}
                  onClick={() => void handleDelete(selectedAppointment)}
                >
                  {deletingId === selectedAppointment.id ? 'Excluindo...' : 'Excluir agendamento'}
                </button>
              </div>
            </section>
          </div>
        )}
      </section>
    </main>
  )
}

function authHeaders(authToken: string): HeadersInit {
  return { Authorization: authToken }
}

function connectionErrorMessage(currentError: unknown, fallbackMessage: string) {
  if (currentError instanceof TypeError) {
    const apiDisplayUrl = API_BASE_URL || 'proxy local /api'
    return `Não consegui conectar com a API em ${apiDisplayUrl}. Verifique se o backend está online e se a URL da API está correta.`
  }

  return currentError instanceof Error ? currentError.message : fallbackMessage
}

function todayInputValue() {
  return localDateInputValue(new Date())
}

function buildWeekDays(weekStart: string): WeekDay[] {
  const startDate = inputValueToLocalDate(weekStart)

  return Array.from({ length: WORK_WEEK_LENGTH }, (_, index) => {
    const currentDate = addDays(startDate, index)
    const currentValue = localDateInputValue(currentDate)

    return {
      value: currentValue,
      weekday: WEEKDAY_LABELS[currentDate.getDay()],
      dayMonth: formatShortDate(currentValue),
    }
  })
}

function startOfWeekInputValue(value: string) {
  const date = inputValueToLocalDate(value)
  const currentWeekday = date.getDay()
  const mondayOffset = currentWeekday === 0 ? -6 : 1 - currentWeekday

  return localDateInputValue(addDays(date, mondayOffset))
}

function addDaysInputValue(value: string, days: number) {
  return localDateInputValue(addDays(inputValueToLocalDate(value), days))
}

function addDays(value: Date, days: number) {
  const nextDate = new Date(value)
  nextDate.setDate(value.getDate() + days)
  return nextDate
}

function inputValueToLocalDate(value: string) {
  const [year, month, day] = value.split('-').map(Number)

  if (!year || !month || !day) {
    return new Date()
  }

  return new Date(year, month - 1, day)
}

function localDateInputValue(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')

  return `${year}-${month}-${day}`
}

function formatDisplayDate(value: string) {
  const [year, month, day] = value.split('-')
  if (!year || !month || !day) {
    return value
  }

  return `${day}/${month}/${year}`
}

function formatShortDate(value: string) {
  const [, month, day] = value.split('-')

  if (!month || !day) {
    return value
  }

  return `${day}/${month}`
}

function compareTimes(left: string, right: string) {
  return timeToMinutes(left) - timeToMinutes(right)
}

function timeToMinutes(value: string) {
  const [hours, minutes] = value.split(':').map(Number)
  return (hours || 0) * 60 + (minutes || 0)
}

function slotPeriodLabel(timeSlot: string) {
  return timeToMinutes(timeSlot) < 12 * 60 ? 'Manhã' : 'Tarde'
}

function statusLabel(status: AppointmentStatus) {
  return EDITABLE_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status
}

function appointmentCountLabel(total: number) {
  return total === 1 ? '1 agendamento' : `${total} agendamentos`
}

function appointmentSlotKey(date: string, time: string) {
  return `${date}|${time}`
}

function isUnavailableSlot(dateValue: string, timeSlot: string) {
  const date = inputValueToLocalDate(dateValue)
  return date.getDay() === 3 && timeSlot === '14:00'
}

export default Agenda
