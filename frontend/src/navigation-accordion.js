/* RiskIQ navigation: two-level accordion inside the Control de mando menu. */
const GROUP_SELECTOR = '.ros-command-menu .side-group'

function setGroupState(group, open) {
  group.classList.toggle('is-open', open)
  const label = group.querySelector('.side-group-label')
  const items = group.querySelectorAll(':scope > button')
  if (!label) return
  label.classList.add('ros-category-trigger')
  label.setAttribute('role', 'button')
  label.setAttribute('tabindex', '0')
  label.setAttribute('aria-expanded', String(open))
  const id = `risk-group-${[...group.parentElement.children].indexOf(group)}`
  label.setAttribute('aria-controls', id)
  items.forEach(button => button.setAttribute('data-risk-nav-item', '1'))
  if (items.length) items[0].parentElement.id = id
}

function enhance(root = document) {
  root.querySelectorAll(GROUP_SELECTOR).forEach(group => {
    if (group.dataset.accordionReady) return
    const label = group.querySelector('.side-group-label')
    if (!label) return
    group.dataset.accordionReady = '1'
    setGroupState(group, false)
    const toggle = event => {
      event.preventDefault()
      event.stopPropagation()
      setGroupState(group, !group.classList.contains('is-open'))
    }
    label.addEventListener('click', toggle)
    label.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') toggle(event)
    })
  })
}

function boot() {
  enhance()
  const observer = new MutationObserver(() => enhance())
  observer.observe(document.body, {childList: true, subtree: true})
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once: true})
else boot()
