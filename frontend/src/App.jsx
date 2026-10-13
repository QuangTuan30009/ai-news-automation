import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import HomePage from './pages/HomePage.jsx'
import NotFound from './pages/NotFound.jsx'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>

      <Toaster position="top-right" />
    </BrowserRouter>
  )
}

export default App
