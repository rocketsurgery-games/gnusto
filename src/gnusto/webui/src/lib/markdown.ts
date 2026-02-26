import { marked } from 'marked'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

export function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/** Escape HTML, style @references, convert newlines to <br> */
export function styleText(text: string): string {
  let html = escapeHtml(text)
  html = html.replace(/@[\w-]+/g, (match) =>
    `<span class="ref" data-entity="${match}" role="button" tabindex="0">${match}</span>`)
  html = html.replace(/\n/g, '<br>')
  return html
}

/** Parse markdown, then style @references in text nodes */
export function styleNarrative(text: string): string {
  let html = marked.parse(text) as string
  html = html.replace(/>([^<]+)</g, (_, textContent: string) => {
    const styled = textContent.replace(/@[\w-]+/g, (match) =>
      `<span class="ref" data-entity="${match}" role="button" tabindex="0">${match}</span>`)
    return '>' + styled + '<'
  })
  return html
}
