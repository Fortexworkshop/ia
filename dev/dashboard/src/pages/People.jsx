import { useEffect, useRef, useState } from 'react'
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
  const [busy, setBusy] = useState(false)
  const fileInput = useRef(null)

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

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  const onPhoto = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    const photo = await asDataUrl(file)
    setForm((current) => ({ ...current, photo }))
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
    } catch (error) {
      setMessage({ error: true, text: `Caméra indisponible : ${error.message}` })
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    if (readOnly) return
    setBusy(true)
    try {
      const result = await peopleApi.save({ ...form, previous })
      const saved = form.name.trim()
      setMessage(
        result.face_error
          ? { error: true, text: `${saved} enregistré, mais le visage n'a pas pu être traité : ${result.face_error}` }
          : { text: `${saved} enregistré${result.person.face ? ', empreinte faciale ajoutée' : ''}.` },
      )
      setForm(EMPTY)
      setPrevious('')
      if (fileInput.current) fileInput.current.value = ''
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
  }

  const remove = async (person) => {
    if (!window.confirm(`Supprimer ${person.name} et son empreinte faciale ?`)) return
    try {
      await peopleApi.remove(person.name)
      setMessage({ text: `${person.name} supprimé.` })
      if (previous === person.name) {
        setForm(EMPTY)
        setPrevious('')
      }
      await refresh()
    } catch (error) {
      setMessage({ error: true, text: error.message })
    }
  }

  return (
    <section>
      <h2>Individus</h2>
      <p className="hint">
        Liste blanche reconnue par l'IA de vision. Les photos sont traitées localement : seule l'empreinte
        faciale est conservée (aucune image enregistrée). Données personnelles, accès restreint.
      </p>

      {readOnly ? (
        <p className="badge">Backend non configuré : données simulées, lecture seule.</p>
      ) : (
        <form className="card form" onSubmit={submit}>
          <h3>{previous ? `Modifier ${previous}` : 'Ajouter un individu'}</h3>
          <div className="fields">
            <label>
              Nom
              <input value={form.name} onChange={update('name')} required maxLength={80} />
            </label>
            <label>
              Rôle
              <input value={form.role} onChange={update('role')} maxLength={80} />
            </label>
            <label className="wide">
              Notes
              <textarea value={form.notes} onChange={update('notes')} rows={2} maxLength={500} />
            </label>
            <label className="wide">
              Photo du visage
              <input ref={fileInput} type="file" accept="image/*" onChange={onPhoto} />
            </label>
          </div>
          <div className="row">
            <button type="submit" className="on" disabled={busy}>
              {previous ? 'Enregistrer' : 'Ajouter'}
            </button>
            <button type="button" onClick={capture} disabled={busy}>
              Prendre une photo
            </button>
            {previous && (
              <button
                type="button"
                onClick={() => {
                  setForm(EMPTY)
                  setPrevious('')
                }}
              >
                Annuler
              </button>
            )}
            {form.photo && <img className="avatar preview" src={form.photo} alt="Aperçu du visage" />}
          </div>
        </form>
      )}

      {message && (
        <p role="status" className={message.error ? 'badge critical' : 'badge ok'}>
          {message.text}
        </p>
      )}

      <div className="grid">
        {people.map((person) => (
          <article className="card person" key={person.name}>
            {person.photoUrl ? (
              <img src={person.photoUrl} alt={person.name} />
            ) : (
              <div className="avatar" aria-hidden="true">{initials(person.name)}</div>
            )}
            <div className="who">
              <b>{person.name}</b>
              {person.role && <p className="hint">{person.role}</p>}
              <p className={person.face ? 'badge ok' : 'badge'}>
                {person.face ? 'Visage enregistré' : 'Sans visage'}
              </p>
              {person.notes && <p className="hint">{person.notes}</p>}
              {!readOnly && (
                <div className="row">
                  <button type="button" onClick={() => edit(person)}>Modifier</button>
                  <button type="button" onClick={() => remove(person)}>Supprimer</button>
                </div>
              )}
            </div>
          </article>
        ))}
        {people.length === 0 && <p className="hint">Aucun individu enregistré.</p>}
      </div>
    </section>
  )
}
