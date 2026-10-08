import { useEffect, useRef, useState } from 'react'
import Icon from '../components/Icon.jsx'
import { peopleApi, simulatedPeople } from '../data/people.js'

const initials = (name) =>
  name.split(' ').filter(Boolean).map((part) => part[0]).join('').slice(0, 2).toUpperCase()

const EMPTY = { name: '', role: '', notes: '', photo: '' }

const asDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('photo illisible'))
    reader.readAsDataURL(file)
  })

export default function People() {
  const readOnly = peopleApi === null
  const [people, setPeople] = useState(readOnly ? simulatedPeople : [])
  const [form, setForm] = useState(EMPTY)
  const [previous, setPrevious] = useState('')
  const [message, setMessage] = useState(null)
  const [nameError, setNameError] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInput = useRef(null)
  const nameInput = useRef(null)
  const formTitle = useRef(null)

  async function refresh() {
    if (readOnly) return
    try {
      setPeople(await peopleApi.list())
    } catch (error) {
      setMessage({ error: true, text: `Liste indisponible : ${error.message}` })
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const update = (field) => (event) => {
    setForm({ ...form, [field]: event.target.value })
    if (field === 'name') setNameError('')
  }

  const onPhoto = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    try {
      const photo = await asDataUrl(file)
      setForm((current) => ({ ...current, photo }))
    } catch (error) {
      setMessage({ error: true, text: error.message })
    }
  }

  const capture = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      const video = document.createElement('video')
      video.srcObject = stream
      await video.play()
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      canvas.getContext('2d').drawImage(video, 0, 0)
      stream.getTracks().forEach((track) => track.stop())
      setForm((current) => ({ ...current, photo: canvas.toDataURL('image/jpeg', 0.9) }))
      setMessage({ text: 'Photo prise. Elle sera transformée en empreinte puis supprimée à l’enregistrement.' })
    } catch (error) {
      setMessage({ error: true, text: `Caméra du navigateur indisponible : ${error.message}` })
    }
  }

  const reset = () => {
    setForm(EMPTY)
    setPrevious('')
    setNameError('')
    if (fileInput.current) fileInput.current.value = ''
  }

  const submit = async (event) => {
    event.preventDefault()
    if (readOnly) return
    if (!form.name.trim()) {
      setNameError('Le nom est obligatoire.')
      nameInput.current?.focus() // RGAA 11.10 : l'erreur est signalée et le focus va au champ
      return
    }
    setBusy(true)
    try {
      const result = await peopleApi.save({ ...form, previous })
      const saved = form.name.trim()
      setMessage(
        result.face_error
          ? { error: true, text: `${saved} enregistré, mais le visage n'a pas pu être traité : ${result.face_error}` }
          : { text: `${saved} enregistré${result.person.face ? ', empreinte faciale ajoutée' : ''}.` },
      )
      reset()
      await refresh()
    } catch (error) {
      setMessage({ error: true, text: error.message })
    } finally {
      setBusy(false)
    }
  }

  const edit = (person) => {
    setForm({ name: person.name, role: person.role, notes: person.notes, photo: '' })
    setPrevious(person.name)
    setMessage(null)
    formTitle.current?.focus()
  }

  const remove = async (person) => {
    if (!window.confirm(`Supprimer ${person.name} et son empreinte faciale ? Cette action est définitive.`)) return
    try {
      await peopleApi.remove(person.name)
      setMessage({ text: `${person.name} supprimé, empreinte faciale effacée.` })
      if (previous === person.name) reset()
      await refresh()
    } catch (error) {
      setMessage({ error: true, text: error.message })
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Individus autorisés</h1>
          <p className="lede">
            Liste blanche reconnue par la caméra. Une personne reconnue n'est pas considérée comme un intrus et peut
            pointer.
          </p>
        </div>
      </div>

      <p className="notice info">
        <Icon name="shield" />
        <span>
          Données biométriques (RGPD, art. 9) : la photo est convertie en empreinte faciale sur le serveur local puis
          supprimée. Aucune image n'est conservée ni envoyée hors du site. Supprimer une personne efface son empreinte.
        </span>
      </p>

      {readOnly && <p className="notice">Serveur non configuré : données d'exemple, lecture seule.</p>}

      {message && (
        <p role="status" className={`notice ${message.error ? 'error' : 'ok'}`}>
          <Icon name={message.error ? 'critical' : 'check'} />
          <span>{message.text}</span>
        </p>
      )}

      {!readOnly && (
        <form className="panel" onSubmit={submit} noValidate aria-labelledby="form-title">
          <h2 id="form-title" ref={formTitle} tabIndex={-1}>
            {previous ? `Modifier ${previous}` : 'Ajouter une personne'}
          </h2>
          <p className="muted small">
            Les champs marqués d'un astérisque (<span className="req">*</span>) sont obligatoires.
          </p>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="p-name">
                Nom et prénom <span className="req">*</span>
              </label>
              <input
                id="p-name"
                ref={nameInput}
                value={form.name}
                onChange={update('name')}
                required
                maxLength={80}
                autoComplete="name"
                aria-invalid={nameError ? 'true' : undefined}
                aria-describedby={nameError ? 'p-name-error' : undefined}
              />
              {nameError && (
                <p id="p-name-error" className="error">
                  {nameError}
                </p>
              )}
            </div>
            <div className="field">
              <label htmlFor="p-role">Fonction</label>
              <input id="p-role" value={form.role} onChange={update('role')} maxLength={80} autoComplete="organization-title" aria-describedby="p-role-help" />
              <p id="p-role-help" className="help">
                Affichée sur le flux vidéo (exemple : Technicien).
              </p>
            </div>
            <div className="field wide">
              <label htmlFor="p-notes">Notes</label>
              <textarea id="p-notes" value={form.notes} onChange={update('notes')} rows={2} maxLength={500} />
            </div>
            <div className="field wide">
              <label htmlFor="p-photo">Photo du visage</label>
              <input id="p-photo" ref={fileInput} type="file" accept="image/*" onChange={onPhoto} aria-describedby="p-photo-help" />
              <p id="p-photo-help" className="help">
                De face, bien éclairé, une seule personne. Formats image courants.
              </p>
            </div>
          </div>
          <div className="btn-row">
            <button type="submit" className="btn primary" disabled={busy}>
              {busy ? 'Enregistrement…' : previous ? 'Enregistrer les modifications' : 'Ajouter'}
            </button>
            <button type="button" className="btn" onClick={capture} disabled={busy}>
              <Icon name="camera" /> Prendre une photo
            </button>
            {previous && (
              <button type="button" className="btn quiet" onClick={reset}>
                Annuler
              </button>
            )}
            {form.photo && <img className="preview" src={form.photo} alt="Aperçu de la photo choisie" width="64" height="64" />}
          </div>
        </form>
      )}

      <section aria-labelledby="list-title">
        <h2 id="list-title" style={{ marginBottom: 'var(--sp-3)' }}>
          {people.length} personne{people.length > 1 ? 's' : ''} enregistrée{people.length > 1 ? 's' : ''}
        </h2>
        {people.length === 0 ? (
          <p className="empty-state panel">
            <Icon name="info" /> Aucune personne enregistrée.
          </p>
        ) : (
          <ul className="people">
            {people.map((person) => (
              <li className="person" key={person.name}>
                <span className="avatar" aria-hidden="true">
                  {initials(person.name)}
                </span>
                <div className="who">
                  <b>{person.name}</b>
                  {person.role && <span className="muted">{person.role}</span>}
                  <span>
                    <span className={`tag ${person.face ? 'ok' : ''}`}>
                      {person.face ? 'Visage enregistré' : 'Sans visage : non reconnu'}
                    </span>
                  </span>
                  {person.notes && <span className="muted small">{person.notes}</span>}
                  {!readOnly && (
                    <div className="btn-row">
                      <button type="button" className="btn small" onClick={() => edit(person)}>
                        Modifier<span className="sr-only"> {person.name}</span>
                      </button>
                      <button type="button" className="btn small danger" onClick={() => remove(person)}>
                        Supprimer<span className="sr-only"> {person.name}</span>
                      </button>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
