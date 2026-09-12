/* Layered ROS navigation: command center -> category -> destination. */
const initCategory = (group) => {
  const label = group.querySelector('.side-group-label')
  if (!label || label.dataset.accordionReady === '1') return

  label.dataset.accordionReady = '1'
  label.setAttribute('role', 'button')
  label.setAttribute('tabindex', '0')
  label.setAttribute('aria-expanded', 'false')
  label.classList.add('ros-category-trigger')

  const setOpen = (open) => {
    group.classList.toggle('is-open', open)
    label.setAttribute('aria-expanded', String(open))
  }

  setOpen(false)

  const toggle = (event) => {
    event.preventDefault()
    event.stopPropagation()
    setOpen(!group.classList.contains('is-open'))
  }

  label.addEventListener('click', toggle)
  label.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') toggle(event)
  })
}

const sync = () => {
  document.querySelectorAll('.ros-command-menu .side-group').forEach(initCategory)
}

document.addEventListener('click', sync, {capture: true})
new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true})
