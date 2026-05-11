import { createContext, useContext, type ReactNode } from 'react'

export type AppLocale = 'en-GB' | 'pt-BR'

export interface I18nCopy {
  appName: string
  appTagline: string
  languageLabel: string
  newStudentCta: string
  separatorOr: string
  returningStudentPlaceholder: string
  continueLearningCta: string
  checkingLabel: string
  enterNameError: string
  noProfileError: (name: string) => string
  serverError: string
  profileProgressTitle: string
  profileDone: string
  profilePhotographer: string
  profileMilestonePath: string
  profileSkills: string
  profileLevelsHint: string
  interviewTitle: string
  interviewNamePlaceholder: string
  interviewChatPlaceholder: string
  interviewSend: string
  teachingPreparingLesson: string
  teachingTodaysFocus: string
  teachingYourAssignment: string
  teachingIntentPlaceholder: string
  teachingSubmitForFeedback: string
  teachingAnalysingPhoto: string
  teachingFeedback: string
  teachingMilestoneReached: (milestone: string) => string
  teachingLoading: string
  teachingTakePhoto: string
  teachingUploadPhoto: string
  teachingRetake: string
  teachingChooseFile: string
  actionRetry: string
  actionAdvance: string
  actionEndLesson: string
}

const TRANSLATIONS: Record<AppLocale, I18nCopy> = {
  'en-GB': {
    appName: 'Photography Coach',
    appTagline: 'Your personal AI photography teacher',
    languageLabel: 'Language',
    newStudentCta: "I'm new here - start learning",
    separatorOr: 'or',
    returningStudentPlaceholder: 'Enter your name to continue...',
    continueLearningCta: 'Continue learning',
    checkingLabel: 'Checking...',
    enterNameError: 'Please enter your name.',
    noProfileError: (name) => `No profile found for "${name}". Start as a new student instead.`,
    serverError: 'Could not connect to the server. Is it running?',
    profileProgressTitle: 'Your progress',
    profileDone: 'Done',
    profilePhotographer: 'Photographer',
    profileMilestonePath: 'Milestone path',
    profileSkills: 'Your skills',
    profileLevelsHint: 'Levels grow each time you submit a strong photo for that skill.',
    interviewTitle: 'Getting to know you',
    interviewNamePlaceholder: 'Enter your first name...',
    interviewChatPlaceholder: 'Type a message...',
    interviewSend: 'Send',
    teachingPreparingLesson: 'Preparing your lesson...',
    teachingTodaysFocus: "Today's focus",
    teachingYourAssignment: 'Your assignment',
    teachingIntentPlaceholder: 'What were you trying to achieve with this shot? (optional)',
    teachingSubmitForFeedback: 'Submit for feedback',
    teachingAnalysingPhoto: 'Analysing your photo...',
    teachingFeedback: 'Feedback',
    teachingMilestoneReached: (milestone) => `Milestone reached: ${milestone}!`,
    teachingLoading: 'Loading...',
    teachingTakePhoto: 'Take photo',
    teachingUploadPhoto: 'Upload photo',
    teachingRetake: 'Retake',
    teachingChooseFile: 'Choose file',
    actionRetry: 'Try again',
    actionAdvance: 'Next challenge',
    actionEndLesson: 'End lesson',
  },
  'pt-BR': {
    appName: 'Mentor de Fotografia',
    appTagline: 'Seu professor pessoal de fotografia com IA',
    languageLabel: 'Idioma',
    newStudentCta: 'Sou novo aqui - começar a aprender',
    separatorOr: 'ou',
    returningStudentPlaceholder: 'Digite seu nome para continuar...',
    continueLearningCta: 'Continuar aprendendo',
    checkingLabel: 'Verificando...',
    enterNameError: 'Por favor, digite seu nome.',
    noProfileError: (name) => `Nenhum perfil encontrado para "${name}". Comece como novo aluno.`,
    serverError: 'Nao foi possivel conectar ao servidor. Ele esta em execucao?',
    profileProgressTitle: 'Seu progresso',
    profileDone: 'Concluir',
    profilePhotographer: 'Fotografo(a)',
    profileMilestonePath: 'Trilha de marcos',
    profileSkills: 'Suas habilidades',
    profileLevelsHint: 'Os niveis sobem cada vez que voce envia uma foto forte nessa habilidade.',
    interviewTitle: 'Conhecendo voce',
    interviewNamePlaceholder: 'Digite seu primeiro nome...',
    interviewChatPlaceholder: 'Digite uma mensagem...',
    interviewSend: 'Enviar',
    teachingPreparingLesson: 'Preparando sua aula...',
    teachingTodaysFocus: 'Foco de hoje',
    teachingYourAssignment: 'Sua tarefa',
    teachingIntentPlaceholder: 'O que voce queria alcancar com esta foto? (opcional)',
    teachingSubmitForFeedback: 'Enviar para feedback',
    teachingAnalysingPhoto: 'Analisando sua foto...',
    teachingFeedback: 'Feedback',
    teachingMilestoneReached: (milestone) => `Marco alcancado: ${milestone}!`,
    teachingLoading: 'Carregando...',
    teachingTakePhoto: 'Tirar foto',
    teachingUploadPhoto: 'Enviar foto',
    teachingRetake: 'Refazer',
    teachingChooseFile: 'Escolher arquivo',
    actionRetry: 'Tentar novamente',
    actionAdvance: 'Proximo desafio',
    actionEndLesson: 'Encerrar aula',
  },
}

const LOCALE_NAMES: Record<AppLocale, string> = {
  'en-GB': 'English (UK)',
  'pt-BR': 'Portugues (BR)',
}

export function localeName(locale: AppLocale): string {
  return LOCALE_NAMES[locale]
}

interface I18nContextValue {
  locale: AppLocale
  setLocale: (locale: AppLocale) => void
  copy: I18nCopy
}

const I18nContext = createContext<I18nContextValue | null>(null)

interface I18nProviderProps extends I18nContextValue {
  children: ReactNode
}

export function I18nProvider({ locale, setLocale, copy, children }: I18nProviderProps) {
  return (
    <I18nContext.Provider value={{ locale, setLocale, copy }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useI18n() {
  const ctx = useContext(I18nContext)
  if (!ctx) {
    throw new Error('useI18n must be used within I18nProvider')
  }
  return ctx
}

export function getCopy(locale: AppLocale): I18nCopy {
  return TRANSLATIONS[locale]
}
