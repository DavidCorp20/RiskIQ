/* RiskIQ workspace accordion controller.
   React owns the page selection; this controller only synchronizes the visual
   open/closed state of the workspace groups so the sidebar never renders as a
   permanently expanded list. */
(() => {
  const MENU = '.ros-command-menu'
  const GROUP = '.side-group'
  const TRIGGER = '.ros-category-trigger'
  let lastActiveGroup = null

  const getMenu = () => document.querySelector(MENU)
  const getGroups = () => [...document.querySelectorAll(`${MENU} ${GROUP}`)]

  const setOpen = (group, open) => {
    if (!group) return
    group.classList.toggle('is-open', open)
    const trigger = group.querySelector(TRIGGER)
    trigger?.setAttribute('aria-expanded', String(open))
    group.querySelectorAll(':scope > button:not(.side-group-label)').forEach(button => {
      button.hidden = !open
    })
  }

  const activeGroupIndex = groups => {
    const active = document.querySelector(`${MENU} button.active`)
    if (!active) return 0
    const group = active.closest(GROUP)
    return Math.max(0, groups.indexOf(group))
  }

  const sync = () => {
    const menu = getMenu()
    const groups = getGroups()
    if (!menu || !groups.length) return

    const activeIndex = activeGroupIndex(groups)
    const previousActive = lastActiveGroup
    lastActiveGroup = activeIndex

    // If React changed the active page, follow it. Otherwise preserve an
    // explicit accordion choice made by the user.
    if (previousActive !== null && previousActive !== activeIndex) {
      delete menu.dataset.openGroup
    }

    const requested = menu.dataset.openGroup
    const openIndex = requested === 'none'
      ? -1
      : requested !== undefined
        ? Number(requested)
        : activeIndex

    groups.forEach((group, index) => setOpen(group, index === openIndex))
  }

  document.addEventListener('click', event => {
    const trigger = event.target.closest?.(`${MENU} ${TRIGGER}`)
    if (trigger) {
      event.preventDefault()
      event.stopPropagation()
      const menu = getMenu()
      const groups = getGroups()
      const group = trigger.closest(GROUP)
      const index = groups.indexOf(group)
      if (!menu || index < 0) return

      menu.dataset.openGroup = group.classList.contains('is-open') ? 'none' : String(index)
      sync()
      return
    }

    // Clicking a page link hands navigation back to React. The next render
    // will open the group containing the new active page.
    const item = event.target.closest?.(`${MENU} ${GROUP} > button:not(.side-group-label)`)
    if (item) {
      const menu = getMenu()
      if (menu) delete menu.dataset.openGroup
    }
  }, true)

  document.addEventListener('keydown', event => {
    if (event.key !== 'Enter' && event.key !== ' ') return
    const trigger = event.target.closest?.(`${MENU} ${TRIGGER}`)
    if (!trigger) return

    event.preventDefault()
    const menu = getMenu()
    const groups = getGroups()
    const group = trigger.closest(GROUP)
    const index = groups.indexOf(group)
    if (!menu || index < 0) return

    menu.dataset.openGroup = group.classList.contains('is-open') ? 'none' : String(index)
    sync()
  })

  new MutationObserver(sync).observe(document.documentElement, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  })

  sync()
})()
