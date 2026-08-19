import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useSystemStatus } from '../status/SystemStatusContext'
import { pluralRu } from '../utils/pluralize'

interface NavDropdownProps {
  label: string
  active: boolean
  items: { to: string; label: string }[]
}

function NavDropdown({ label, active, items }: NavDropdownProps) {
  return (
    <div className={`layout__nav-dropdown${active ? ' layout__nav-dropdown--active' : ''}`}>
      <span className="layout__nav-dropdown__trigger">{label}</span>
      <div className="layout__nav-dropdown__menu">
        {items.map((item) => (
          <Link key={item.to} to={item.to}>
            {item.label}
          </Link>
        ))}
      </div>
    </div>
  )
}

function SystemStatusIndicator() {
  const activeJobs = useSystemStatus()
  if (activeJobs === null) return null

  const busy = activeJobs > 0
  return (
    <div className={`system-status${busy ? ' system-status--busy' : ' system-status--idle'}`}>
      <span className="system-status__dot" />
      {busy ? `Идёт ${activeJobs} ${pluralRu(activeJobs, 'расчёт', 'расчёта', 'расчётов')}` : 'Свободно'}
    </div>
  )
}

export function Layout({ children, wide }: { children: ReactNode; wide?: boolean }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname } = useLocation()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const solveActive = pathname === '/solve' || pathname === '/batches/new'
  const compareActive = pathname.startsWith('/compare')

  return (
    <div className="layout">
      <header className="layout__header">
        <nav className="layout__nav">
          <NavDropdown
            label="Решить"
            active={solveActive}
            items={[
              { to: '/solve', label: 'Решить' },
              { to: '/batches/new', label: 'Решить группу' },
            ]}
          />
          <NavDropdown
            label="Сравнить"
            active={compareActive}
            items={[
              { to: '/compare', label: 'Сравнить решения' },
              { to: '/compare/batches', label: 'Сравнить группы' },
            ]}
          />
          <Link to="/history">История</Link>
          <Link to="/tokens">API-токены</Link>
          {user?.is_admin && <Link to="/users">Пользователи</Link>}
        </nav>
        {user && (
          <div className="layout__user">
            <SystemStatusIndicator />
            <span>{user.username}</span>
            <button type="button" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        )}
      </header>
      <main className={`layout__content${wide ? ' layout__content--wide' : ''}`}>{children}</main>
    </div>
  )
}
