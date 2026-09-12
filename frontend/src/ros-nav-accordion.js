/* RiskIQ navigation controller: category accordions only. */
const initCategory = (group) => {
  const trigger = group.querySelector('.ros-category-trigger')
  if (!trigger || trigger.dataset.accordionReady === '1') return

  trigger.dataset.accordionReady = '1'
  trigger.setAttribute('aria-expanded', 'false')

  const setOpen = (open) => {
    group.classList.toggle('is-open', open)
    trigger.setAttribute('aria-expanded', String(open))
  }

  const toggle = (event) => {
    event.preventDefault()
    event.stopPropagation()
    setOpen(!group.classList.contains('is-open'))
  }

  trigger.addEventListener('click', toggle)
  trigger.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') toggle(event)
  })
}

const sync = () => {
  document.querySelectorAll('.ros-command-menu .side-group').forEach(initCategory)
}

new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true})
sync()
