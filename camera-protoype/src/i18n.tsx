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
  // Camera live cues
  cameraDark: string
  cameraBright: string
  cameraTiltLeft: string
  cameraTiltRight: string
  cameraTiltedBadge: (deg: number) => string
  cameraOpening: string
  cameraNoFace: string
  cameraSkillTips: Record<string, string[]>
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
    cameraDark: 'Scene is very dark — move to better light',
    cameraBright: 'Very bright — avoid shooting into light',
    cameraTiltLeft: 'Camera tilting left — straighten your frame',
    cameraTiltRight: 'Camera tilting right — straighten your frame',
    cameraTiltedBadge: (deg) => `← Tilted ${deg}°`,
    cameraOpening: 'Opening camera…',
    cameraNoFace: 'No face visible — position a person in the frame for portrait practice',
    cameraSkillTips: {
      composition: [
        'Place your subject on a grid line',
        'Leave breathing room in the direction they face',
        'Try a different angle or distance',
      ],
      lighting: [
        'Watch for harsh shadows on your subject',
        'Soft, diffused light flatters most subjects',
        'Avoid shooting directly into a bright window',
      ],
      subject_clarity: [
        'Create distance between subject and background',
        'Get closer to fill the frame with your subject',
        'Focus on your subject\'s eyes',
      ],
      pose_expression: [
        'Ask your subject to relax their shoulders',
        'Try a slight turn — avoid facing straight-on',
        'Wait for a natural, candid moment',
      ],
      background_control: [
        'Check what\'s directly behind your subject',
        'Move to a cleaner, simpler background',
        'Look for distracting lines or objects',
      ],
    },
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
    cameraDark: 'Cena muito escura — va para uma luz melhor',
    cameraBright: 'Muito brilhante — evite fotografar contra a luz',
    cameraTiltLeft: 'Camera inclinando para a esquerda — endireite o quadro',
    cameraTiltRight: 'Camera inclinando para a direita — endireite o quadro',
    cameraTiltedBadge: (deg) => `← Inclinado ${deg}°`,
    cameraOpening: 'Abrindo camera…',
    cameraNoFace: 'Nenhum rosto visivel — posicione uma pessoa no quadro para praticar retrato',
    cameraSkillTips: {
      composition: [
        'Coloque seu sujeito em uma linha da grade',
        'Deixe espaco de respiro na direcao que ele olha',
        'Tente um angulo ou distancia diferentes',
      ],
      lighting: [
        'Observe sombras duras no seu sujeito',
        'Luz suave e difusa favorece a maioria dos sujeitos',
        'Evite fotografar diretamente para uma janela brilhante',
      ],
      subject_clarity: [
        'Crie distancia entre o sujeito e o fundo',
        'Aproxime-se para preencher o quadro com seu sujeito',
        'Foque nos olhos do seu sujeito',
      ],
      pose_expression: [
        'Peca ao sujeito para relaxar os ombros',
        'Tente uma leve virada — evite ficar de frente',
        'Aguarde um momento natural e espontaneo',
      ],
      background_control: [
        'Verifique o que esta diretamente atras do sujeito',
        'Mova para um fundo mais limpo e simples',
        'Procure linhas ou objetos que distraiam',
      ],
    },
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
