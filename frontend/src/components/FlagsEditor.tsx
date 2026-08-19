import { useState, type ReactNode } from 'react'

interface Props {
  parameterNames: string[]
  values: Record<string, string>
  onChange: (values: Record<string, string>) => void
  disabled?: boolean
}

const MAX_SUGGESTIONS = 8

function highlightMatch(name: string, query: string): ReactNode {
  const idx = name.toLowerCase().indexOf(query)
  if (idx === -1 || query === '') return name
  return (
    <>
      {name.slice(0, idx)}
      <mark>{name.slice(idx, idx + query.length)}</mark>
      {name.slice(idx + query.length)}
    </>
  )
}

export function FlagsEditor({ parameterNames, values, onChange, disabled }: Props) {
  const [query, setQuery] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)

  const trimmedQuery = query.trim().toLowerCase()
  const suggestions = trimmedQuery
    ? parameterNames
        .filter((name) => name.toLowerCase().includes(trimmedQuery) && !(name in values))
        .slice(0, MAX_SUGGESTIONS)
    : []

  function addParameter(name: string) {
    onChange({ ...values, [name]: '' })
    setQuery('')
    setShowSuggestions(false)
  }

  function setValue(name: string, value: string) {
    onChange({ ...values, [name]: value })
  }

  function removeParameter(name: string) {
    const { [name]: _removed, ...rest } = values
    onChange(rest)
  }

  return (
    <div className="flags-editor">
      <div className="flags-editor__search">
        <input
          placeholder="Начните вводить имя параметра…"
          value={query}
          disabled={disabled}
          onChange={(e) => {
            setQuery(e.target.value)
            setShowSuggestions(true)
          }}
          onFocus={() => setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
        />
        {showSuggestions && suggestions.length > 0 && (
          <ul className="flags-editor__suggestions">
            {suggestions.map((name) => (
              <li key={name} onMouseDown={() => addParameter(name)}>
                {highlightMatch(name, trimmedQuery)}
              </li>
            ))}
          </ul>
        )}
      </div>

      {Object.keys(values).length > 0 && (
        <div className="flags-editor__rows">
          {Object.entries(values).map(([name, value]) => (
            <div key={name} className="flags-editor__row">
              <span className="flags-editor__row-name">{name}</span>
              <input
                placeholder="значение"
                value={value}
                disabled={disabled}
                onChange={(e) => setValue(name, e.target.value)}
              />
              <button
                type="button"
                className="flags-editor__remove"
                disabled={disabled}
                onClick={() => removeParameter(name)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
