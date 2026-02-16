export type ReportParticipantInteraction = {
  participant: string
  interactedWith: string
}

export type ReportMlUsage = {
  activity: string
  activityType: string
  usedBy: string
  usedAt: string
  model: string
  modelLabel: string
  version: string
  dataset: string
  datasetLabel: string
  score: string
}

export type ReportEmotionSample = {
  t: string
  sourceActivity: string
  targetEntity: string
  targetType: string
  targetLabel: string
  category: string
  intensity: string
  confidence: string
}

export type ReportStateSample = {
  robot: string
  robotName: string
  t: string
  location: string
}

export type ReportDisplacementSummary = {
  robot: string
  samples: number
  locationChanges: number
  path: string
}
