interface Props {
  percent: number
}

export function UploadProgressBar({ percent }: Props) {
  const done = percent >= 100
  return (
    <div className="upload-progress">
      <div className="upload-progress__bar">
        <div className="upload-progress__bar-fill" style={{ width: `${percent}%` }} />
      </div>
      <div className="upload-progress__label">
        {done ? 'Файл загружен, ждём начала решения…' : `Загрузка файла… ${percent}%`}
      </div>
    </div>
  )
}
