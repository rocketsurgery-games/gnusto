import '@fontsource/comic-neue/400.css'
import '@fontsource/comic-neue/700.css'
import './tokens.css'
import './global.css'
import { mount } from 'svelte'
import App from './App.svelte'

const app = mount(App, { target: document.getElementById('app')! })

export default app
