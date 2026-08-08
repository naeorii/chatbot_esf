import Chatbot from './pages/Chatbot'
import Agenda from './pages/Agenda'

function App() {
  if (window.location.pathname.startsWith('/agenda')) {
    return <Agenda />
  }

  return <Chatbot />
}

export default App
