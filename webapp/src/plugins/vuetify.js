import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#13ec5b',
          background: '#102216',
          surface: '#1c2e24',
          'surface-variant': '#15261d',
          'on-surface': '#ffffff',
          secondary: '#9db9a6',
          error: '#ef4444',
          info: '#3b82f6',
          warning: '#f59e0b',
        }
      }
    }
  },
  defaults: {
    VBtn: { rounded: 'lg' },
    VCard: { rounded: 'xl' },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect: { variant: 'outlined', density: 'comfortable' },
  }
})
