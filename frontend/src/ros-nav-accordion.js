/* RiskIQ navigation controller: command center -> category -> destination. */
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

const initCommand = () => {
  const shell = document.querySelector('.ros-command-select')
  const trigger = shell?.querySelector('.ros-command-trigger')
  if (!shell || !trigger || trigger.dataset.navReady === '1') return

  trigger.dataset.navReady = '1'
  shell.classList.remove('nav-open')
  trigger.setAttribute('aria-expanded', 'false')
  const indicator = trigger.querySelector(':scope > strong')

  const toggle = (event) => {
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    const open = !shell.classList.contains('nav-open')
    shell.classList.toggle('nav-open', open)
    trigger.setAttribute('aria-expanded', String(open))
    if (indicator) indicator.textContent = open ? '⌃' : '⌄'
  }

  trigger.addEventListener('click', toggle, true)
  trigger.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') toggle(event)
  }, true)
}

const sync = () => {
  initCommand()
  document.querySelectorAll('.ros-command-menu .side-group').forEach(initCategory)
}

new MutationObserver(sync).observe(document.documentElement, {childList: true, subtree: true})
sync()
