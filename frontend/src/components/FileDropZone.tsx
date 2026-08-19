import { useRef, useState, type DragEvent } from 'react'

interface Props {
  file: File | null
  onFileSelected: (file: File) => void
  disabled?: boolean
  accept?: string
  placeholder?: string
}

export function FileDropZone({
  file,
  onFileSelected,
  disabled,
  accept = '.mps,.mps.gz,.mps.bz2',
  placeholder = 'Перетащите MPS-файл сюда или нажмите, чтобы выбрать',
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault()
    setDragOver(false)
    if (disabled) return
    const dropped = e.dataTransfer.files[0]
    if (dropped) onFileSelected(dropped)
  }

  return (
    <div
      className={`dropzone${dragOver ? ' dropzone--over' : ''}${disabled ? ' dropzone--disabled' : ''}`}
      onDragOver={(e) => {
        e.preventDefault()
        if (!disabled) setDragOver(true)
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        hidden
        disabled={disabled}
        onChange={(e) => {
          const selected = e.target.files?.[0]
          if (selected) onFileSelected(selected)
        }}
      />
      {file ? (
        <div className="dropzone__file">
          <span className="dropzone__filename">{file.name}</span>
          <span className="dropzone__filesize">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
        </div>
      ) : (
        <div className="dropzone__placeholder">{placeholder}</div>
      )}
    </div>
  )
}
