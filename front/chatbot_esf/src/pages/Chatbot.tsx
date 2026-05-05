import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'

type Sender = 'bot' | 'user'

type ChatMessage = {
  id: string
  sender: Sender
  text: string
  map?: ChatMap
}

type ChatOption = {
  id: string
  label: string
}

type ChatMap = {
  latitude: number
  longitude: number
  label: string
  address: string
}

type ChatResponse = {
  current_node: string
  messages: string[]
  options: ChatOption[]
  ended: boolean
  map?: ChatMap | null
}

const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const addressMarkerIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})

let messageSequence = 0

function createMessage(sender: Sender, text: string, map?: ChatMap): ChatMessage {
  messageSequence += 1
  return {
    id: `${sender}-${messageSequence}`,
    sender,
    text,
    map,
  }
}

function createBotMessages(texts: string[], map?: ChatMap | null): ChatMessage[] {
  return texts.map((text, index) => createMessage('bot', text, index === 0 ? map ?? undefined : undefined))
}

function PrinterIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 7V3H17V7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path
        d="M7 17H5C3.9 17 3 16.1 3 15V10C3 8.9 3.9 8 5 8H19C20.1 8 21 8.9 21 10V15C21 16.1 20.1 17 19 17H17"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path d="M7 14H17V21H7V14Z" stroke="currentColor" strokeWidth="2" />
      <path d="M17 11H17.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function BotIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C10.9 2 10 2.9 10 4V5.1C6.6 5.6 4 8.5 4 12V18C4 19.1 4.9 20 6 20H18C19.1 20 20 19.1 20 18V12C20 8.5 17.4 5.6 14 5.1V4C14 2.9 13.1 2 12 2ZM8 13C8.6 13 9 12.6 9 12C9 11.4 8.6 11 8 11C7.4 11 7 11.4 7 12C7 12.6 7.4 13 8 13ZM16 13C16.6 13 17 12.6 17 12C17 11.4 16.6 11 16 11C15.4 11 15 11.4 15 12C15 12.6 15.4 13 16 13Z" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 3H14L19 8V21H7V3Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <path d="M14 3V8H19" stroke="currentColor" strokeWidth="2" />
      <path d="M10 13H16M10 17H16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function ClockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="8" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8V12L15 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M8 11C10.2 11 12 9.2 12 7C12 4.8 10.2 3 8 3C5.8 3 4 4.8 4 7C4 9.2 5.8 11 8 11Z" stroke="currentColor" strokeWidth="2" />
      <path d="M2.5 21C3.2 17.9 5.2 16 8 16C10.8 16 12.8 17.9 13.5 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M16 11C17.7 11 19 9.7 19 8C19 6.3 17.7 5 16 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M15.5 16C18.1 16.2 19.8 17.9 20.5 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

function LocationIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 21C15.5 17.4 18 14.2 18 10C18 6.7 15.3 4 12 4C8.7 4 6 6.7 6 10C6 14.2 8.5 17.4 12 21Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
      <circle cx="12" cy="10" r="2.5" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}

function HomeIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M4 11L12 4L20 11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M6 10V20H18V10" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
    </svg>
  )
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M7 7L17 17M17 7L7 17" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M9 6L15 12L9 18" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function getOptionIcon(optionId: string) {
  if (optionId === 'horario') {
    return <ClockIcon />
  }

  if (optionId === 'grupos' || optionId === 'equipe') {
    return <UsersIcon />
  }

  if (optionId === 'endereco') {
    return <LocationIcon />
  }

  if (optionId === 'voltar_inicio') {
    return <HomeIcon />
  }

  if (optionId === 'encerrar') {
    return <CloseIcon />
  }

  return <FileIcon />
}

function AddressMapView({ map }: { map: ChatMap }) {
  const mapContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!mapContainerRef.current) {
      return undefined
    }

    const leafletMap = L.map(mapContainerRef.current, {
      scrollWheelZoom: false,
      zoomControl: false,
    }).setView([map.latitude, map.longitude], 16)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(leafletMap)

    L.marker([map.latitude, map.longitude], { icon: addressMarkerIcon }).addTo(leafletMap).bindPopup(map.label)

    window.setTimeout(() => {
      leafletMap.invalidateSize()
    }, 0)

    return () => {
      leafletMap.remove()
    }
  }, [map])

  const mapUrl = `https://www.openstreetmap.org/?mlat=${map.latitude}&mlon=${map.longitude}#map=17/${map.latitude}/${map.longitude}`

  return (
    <div className="address-map-card">
      <div className="address-map" ref={mapContainerRef} aria-label={`Mapa de ${map.label}`} />
      <a className="address-map-link" href={mapUrl} target="_blank" rel="noreferrer">
        Abrir mapa
      </a>
    </div>
  )
}

function Chatbot() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [options, setOptions] = useState<ChatOption[]>([])
  const [inputValue, setInputValue] = useState('')
  const [currentNode, setCurrentNode] = useState('inicio')
  const [isLoading, setIsLoading] = useState(false)
  const [ended, setEnded] = useState(false)
  const chatBodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true

    async function loadInitialMessage() {
      setIsLoading(true)

      try {
        const response = await fetch(`${API_BASE_URL}/api/chat/start`)
        if (!response.ok) {
          throw new Error('Falha ao iniciar conversa')
        }

        const data = (await response.json()) as ChatResponse
        if (!active) {
          return
        }

        setMessages(createBotMessages(data.messages, data.map))
        setOptions(data.options)
        setCurrentNode(data.current_node)
        setEnded(data.ended)
      } catch {
        if (!active) {
          return
        }

        setMessages([
          createMessage(
            'bot',
            'Nao consegui conectar com a API. Verifique se o FastAPI esta rodando em http://localhost:8000.',
          ),
        ])
        setOptions([])
      } finally {
        if (active) {
          setIsLoading(false)
        }
      }
    }

    loadInitialMessage()

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    chatBodyRef.current?.scrollTo({
      top: chatBodyRef.current.scrollHeight,
      behavior: 'smooth',
    })
  }, [messages, options, isLoading])

  async function requestChat(payload: { message?: string; option_id?: string }) {
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...payload,
          current_node: currentNode,
        }),
      })

      if (!response.ok) {
        throw new Error('Falha na resposta da API')
      }

      const data = (await response.json()) as ChatResponse
      setMessages((currentMessages) => [
        ...currentMessages,
        ...createBotMessages(data.messages, data.map),
      ])
      setOptions(data.options)
      setCurrentNode(data.current_node)
      setEnded(data.ended)
    } catch {
      setMessages((currentMessages) => [
        ...currentMessages,
        createMessage('bot', 'Nao consegui falar com a API agora. Tente novamente em instantes.'),
      ])
    } finally {
      setIsLoading(false)
    }
  }

  function handleOptionClick(option: ChatOption) {
    if (isLoading || ended) {
      return
    }

    setMessages((currentMessages) => [...currentMessages, createMessage('user', option.label)])
    setOptions([])
    void requestChat({ option_id: option.id })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedMessage = inputValue.trim()
    if (!trimmedMessage || isLoading || ended) {
      return
    }

    setInputValue('')
    setMessages((currentMessages) => [...currentMessages, createMessage('user', trimmedMessage)])
    setOptions([])
    void requestChat({ message: trimmedMessage })
  }

  return (
    <main className="chatbot-page">
      <section className="chat-container" aria-label="Chatbot UBS">
        <header className="chat-header">
          <div className="header-icon">
            <PrinterIcon />
          </div>

          <div className="header-text">
            <h1>ESF São Carlos</h1>
            <p>Assistente Virtual - UBS</p>
          </div>

          <div className={`status ${ended ? 'status-ended' : ''}`}>
            <span className="status-dot" />
            {ended ? 'Encerrado' : 'Ativo'}
          </div>
        </header>

        <div className="chat-body" ref={chatBodyRef}>
          <div className="date-badge">Conversa iniciada agora</div>

          {messages.map((message) =>
            message.sender === 'bot' ? (
              <div className="message-row" key={message.id}>
                <div className="bot-avatar">
                  <BotIcon />
                </div>
                <div className={`bot-message ${message.map ? 'bot-message-with-map' : ''}`}>
                  <div>{message.text}</div>
                  {message.map && <AddressMapView map={message.map} />}
                </div>
              </div>
            ) : (
              <div className="user-message-row" key={message.id}>
                <div className="user-message">{message.text}</div>
              </div>
            ),
          )}

          {isLoading && (
            <div className="message-row">
              <div className="bot-avatar">
                <BotIcon />
              </div>
              <div className="bot-message typing-message">Digitando...</div>
            </div>
          )}

          {options.length > 0 && !isLoading && !ended && (
            <div className="options" aria-label="Opcoes de atendimento">
              {options.map((option) => (
                <button className="option-button" type="button" key={option.id} onClick={() => handleOptionClick(option)}>
                  <span className="option-icon">{getOptionIcon(option.id)}</span>
                  <span className="option-text">{option.label}</span>
                  <span className="option-arrow" aria-hidden="true">
                    <ChevronRightIcon />
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        <footer className="chat-footer">
          <form className="input-box" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder={ended ? 'Atendimento encerrado' : 'Escreva sua mensagem...'}
              aria-label="Mensagem"
              value={inputValue}
              disabled={isLoading || ended}
              onChange={(event) => setInputValue(event.target.value)}
            />
            <button className="send-button" type="submit" aria-label="Enviar mensagem" disabled={isLoading || ended} />
          </form>

          <p className="footer-text">Atendimento automatizado - Dados protegidos pela LGPD</p>
        </footer>
      </section>
    </main>
  )
}

export default Chatbot
