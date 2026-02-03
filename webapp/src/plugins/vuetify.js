import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'light',
    themes: {
      light: {
        colors: {
          primary: '#10b981',
          background: '#fafafa',
          surface: '#ffffff',
          'on-surface': '#171717',
          secondary: '#737373',
          error: '#dc2626',
          info: '#3b82f6',
          warning: '#f59e0b',
        }
      },
      dark: {
        colors: {
          primary: '#10b981',
          background: '#171717',
          surface: '#262626',
          'on-surface': '#fafafa',
          secondary: '#a3a3a3',
          error: '#dc2626',
          info: '#3b82f6',
          warning: '#f59e0b',
        }
      }
    }
  },
  defaults: {
    VBtn: { rounded: 'lg', variant: 'flat', elevation: 0 },
    VCard: { rounded: 'lg', elevation: 0 },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect: { variant: 'outlined', density: 'comfortable' },
  }
})
