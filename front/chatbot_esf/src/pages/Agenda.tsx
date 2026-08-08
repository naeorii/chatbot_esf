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

const API_BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const AUTH_STORAGE_KEY = 'esf-agenda-auth'

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
  const [dateFilter, setDateFilter] = useState(todayInputValue())
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('todos')
  const [authToken, setAuthToken] = useState(() => sessionStorage.getItem(AUTH_STORAGE_KEY) ?? '')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [updatingId, setUpdatingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [error, setError] = useState('')

  const totals = useMemo(() => {
    return appointments.reduce(
      (summary, appointment) => {
        summary.total += 1
        summary[appointment.status] += 1
        return summary
      },
      { total: 0, novo: 0, confirmado: 0, cancelado: 0, atendido: 0 },
    )
  }, [appointments])

  const loadAppointments = useCallback(async () => {
    if (!authToken) {
      return
    }

    setIsLoading(true)
    setError('')

    const params = new URLSearchParams()
    if (dateFilter) {
      params.set('date', dateFilter)
    }

    if (statusFilter !== 'todos') {
      params.set('status', statusFilter)
    }

    const queryString = params.toString()

    try {
      const response = await fetch(`${API_BASE_URL}/api/appointments${queryString ? `?${queryString}` : ''}`, {
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
    } catch (currentError) {
      setAppointments([])
      setError(connectionErrorMessage(currentError, 'Erro ao carregar agendamentos.'))
    } finally {
      setIsLoading(false)
    }
  }, [authToken, dateFilter, statusFilter])

  useEffect(() => {
    void loadAppointments()
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

  function handleLogout() {
    sessionStorage.removeItem(AUTH_STORAGE_KEY)
    setAuthToken('')
    setAppointments([])
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
      setAppointments((currentAppointments) =>
        currentAppointments.map((appointment) =>
          appointment.id === updatedAppointment.id ? updatedAppointment : appointment,
        ),
      )
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

      if (!response.ok) {
        throw new Error('Não foi possível excluir o agendamento.')
      }

      setAppointments((currentAppointments) =>
        currentAppointments.filter((currentAppointment) => currentAppointment.id !== appointment.id),
      )
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
          <div>
            <span className="agenda-eyebrow">ESF São Carlos/Urlândia</span>
            <h1>Agenda da unidade</h1>
          </div>

          <button className="agenda-secondary-button" type="button" onClick={handleLogout}>
            Sair
          </button>
        </header>

        <section className="agenda-toolbar" aria-label="Filtros da agenda">
          <label>
            Data
            <input type="date" value={dateFilter} onChange={(event) => setDateFilter(event.target.value)} />
          </label>

          <label>
            Status
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
              {STATUS_OPTIONS.map((option) => (
                <option value={option.value} key={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="agenda-toolbar-actions">
            <button className="agenda-primary-button" type="button" onClick={() => void loadAppointments()}>
              Atualizar
            </button>
          </div>
        </section>

        <section className="agenda-summary" aria-label="Resumo">
          <div>
            <span>Total</span>
            <strong>{totals.total}</strong>
          </div>
          <div>
            <span>Novos</span>
            <strong>{totals.novo}</strong>
          </div>
          <div>
            <span>Confirmados</span>
            <strong>{totals.confirmado}</strong>
          </div>
          <div>
            <span>Atendidos</span>
            <strong>{totals.atendido}</strong>
          </div>
        </section>

        {error && <p className="agenda-error">{error}</p>}

        <section className="agenda-list" aria-label="Agendamentos">
          <div className="agenda-list-header">
            <span>Horário</span>
            <span>Paciente</span>
            <span>Serviço</span>
            <span>Profissional</span>
            <span>Status</span>
            <span>Ações</span>
          </div>

          {isLoading ? (
            <div className="agenda-empty">Carregando agendamentos...</div>
          ) : appointments.length === 0 ? (
            <div className="agenda-empty">Nenhum agendamento encontrado.</div>
          ) : (
            appointments.map((appointment) => (
              <article className="agenda-row" key={appointment.id}>
                <div className="agenda-time">
                  <strong>{appointment.appointment_time}</strong>
                  <span>{formatDisplayDate(appointment.appointment_date)}</span>
                </div>

                <div className="agenda-patient">
                  <strong>{appointment.patient_name}</strong>
                  <span>{appointment.document_masked}</span>
                </div>

                <div>{appointment.service}</div>
                <div>{appointment.professional}</div>

                <label className={`agenda-status agenda-status-${appointment.status}`}>
                  <span className="sr-only">Status</span>
                  <select
                    value={appointment.status}
                    disabled={updatingId === appointment.id}
                    onChange={(event) =>
                      void handleStatusChange(appointment.id, event.target.value as AppointmentStatus)
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
                  disabled={deletingId === appointment.id || updatingId === appointment.id}
                  onClick={() => void handleDelete(appointment)}
                >
                  {deletingId === appointment.id ? 'Excluindo...' : 'Excluir'}
                </button>
              </article>
            ))
          )}
        </section>
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
  const today = new Date()
  today.setMinutes(today.getMinutes() - today.getTimezoneOffset())
  return today.toISOString().slice(0, 10)
}

function formatDisplayDate(value: string) {
  const [year, month, day] = value.split('-')
  if (!year || !month || !day) {
    return value
  }

  return `${day}/${month}/${year}`
}

export default Agenda
