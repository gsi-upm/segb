export const reportQueries = {
  participantsHumans: `
PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
PREFIX oro: <http://kb.openrobots.org#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX schema: <http://schema.org/>

SELECT
  ?participant
  (GROUP_CONCAT(DISTINCT COALESCE(?robotName, STR(?robot)); separator="__SEGB_LINE_BREAK__") AS ?interactedRobots)
WHERE {
  ?sharedEvent a schema:Event ;
               schema:about ?human .
  ?human a oro:Human .
  OPTIONAL { ?human foaf:firstName ?humanName }
  BIND(COALESCE(?humanName, STR(?human)) AS ?participant)

  ?activity a segb:LoggedActivity ;
            segb:wasPerformedBy ?robot ;
            schema:about ?sharedEvent .
  ?robot a oro:Robot .
  OPTIONAL { ?robot oro:hasName ?robotName }
}
GROUP BY ?participant
ORDER BY ?participant
`,

  participantsRobots: `
PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
PREFIX oro: <http://kb.openrobots.org#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX schema: <http://schema.org/>

SELECT
  ?participant
  (GROUP_CONCAT(DISTINCT COALESCE(?humanName, STR(?human)); separator="__SEGB_LINE_BREAK__") AS ?interactedHumans)
  (GROUP_CONCAT(DISTINCT COALESCE(?otherRobotName, STR(?otherRobot)); separator="__SEGB_LINE_BREAK__") AS ?interactedRobots)
WHERE {
  ?activity a segb:LoggedActivity ;
            segb:wasPerformedBy ?robot ;
            schema:about ?sharedEvent .
  ?robot a oro:Robot .
  OPTIONAL { ?robot oro:hasName ?robotName }
  BIND(COALESCE(?robotName, STR(?robot)) AS ?participant)

  OPTIONAL {
    ?sharedEvent schema:about ?human .
    ?human a oro:Human .
    OPTIONAL { ?human foaf:firstName ?humanName }
  }

  OPTIONAL {
    ?otherActivity a segb:LoggedActivity ;
                   segb:wasPerformedBy ?otherRobot ;
                   schema:about ?sharedEvent .
    ?otherRobot a oro:Robot .
    FILTER (?otherRobot != ?robot)
    OPTIONAL { ?otherRobot oro:hasName ?otherRobotName }
  }
}
GROUP BY ?participant
ORDER BY ?participant
`,

  mlUsage: `
PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
PREFIX mls: <http://www.w3.org/ns/mls#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX oro: <http://kb.openrobots.org#>
PREFIX prov: <http://www.w3.org/ns/prov#>

SELECT ?activity ?activityType ?usedBy ?usedByName ?startedAt ?model ?modelLabel ?version ?dataset ?datasetLabel ?score
WHERE {
  ?activity a segb:LoggedActivity ;
            segb:usedMLModel ?model ;
            segb:wasPerformedBy ?usedBy .
  OPTIONAL { ?activity a ?activityType . FILTER(?activityType != segb:LoggedActivity) }
  OPTIONAL { ?usedBy oro:hasName ?usedByName }
  OPTIONAL { ?activity prov:startedAtTime ?startedAt }
  OPTIONAL { ?model rdfs:label ?modelLabel }
  OPTIONAL { ?model schema:version ?version }

  OPTIONAL {
    ?run a mls:Run ;
         mls:hasOutput ?model ;
         mls:hasInput ?dataset .
    OPTIONAL { ?dataset rdfs:label ?datasetLabel }
    OPTIONAL {
      ?run mls:hasOutput ?eval .
      ?eval a mls:ModelEvaluation ;
            mls:hasValue ?score .
    }
  }
}
ORDER BY ?startedAt ?activity
`,

  emotionTimeline: `
PREFIX onyx: <http://www.gsi.upm.es/ontologies/onyx/ns#>
PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX oro: <http://kb.openrobots.org#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT
  ?t
  ?sourceActivity
  ?sourceActivityLabel
  ?triggerActivity
  ?triggerActivityLabel
  ?triggerEntity
  ?triggerEntityLabel
  ?triggerMessageText
  ?targetEntity
  ?targetType
  ?targetLabel
  ?category
  ?intensity
  ?confidence
WHERE {
  ?sourceActivity a onyx:EmotionAnalysis ;
                 prov:startedAtTime ?t ;
                 segb:producedEntityResult ?annotation .
  ?annotation onyx:hasEmotion ?emotion ;
              oa:hasTarget ?targetEntity .
  ?emotion onyx:hasEmotionCategory ?category ;
           onyx:hasEmotionIntensity ?intensity .
  OPTIONAL { ?emotion onyx:algorithmConfidence ?confidence }
  OPTIONAL { ?sourceActivity rdfs:label ?sourceActivityLabel }

  OPTIONAL {
    ?sourceActivity segb:triggeredByActivity ?triggerActivity .
    OPTIONAL { ?triggerActivity rdfs:label ?triggerActivityLabel }
  }
  OPTIONAL {
    ?sourceActivity segb:triggeredByEntity ?triggerEntity .
    OPTIONAL { ?triggerEntity rdfs:label ?triggerEntityLabel }
    OPTIONAL { ?triggerEntity oro:hasText ?triggerMessageText }
  }

  OPTIONAL {
    ?targetEntity a oro:Robot .
    OPTIONAL { ?targetEntity oro:hasName ?robotName }
    BIND("robot" AS ?targetType)
    BIND(COALESCE(?robotName, STR(?targetEntity)) AS ?targetLabel)
  }
  OPTIONAL {
    ?targetEntity a prov:Person .
    OPTIONAL { ?targetEntity foaf:firstName ?personName }
    BIND("human" AS ?targetType)
    BIND(COALESCE(?personName, STR(?targetEntity)) AS ?targetLabel)
  }
  FILTER(BOUND(?targetType))
}
ORDER BY ?t DESC(?intensity)
`,

  extremeEmotion: `
PREFIX onyx: <http://www.gsi.upm.es/ontologies/onyx/ns#>
PREFIX segb: <http://www.gsi.upm.es/ontologies/segb/ns#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX oro: <http://kb.openrobots.org#>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?t ?sourceActivity ?targetEntity ?targetType ?targetLabel ?category ?intensity ?confidence
WHERE {
  ?sourceActivity a onyx:EmotionAnalysis ;
                 prov:startedAtTime ?t ;
                 segb:producedEntityResult ?annotation .
  ?annotation onyx:hasEmotion ?emotion ;
              oa:hasTarget ?targetEntity .
  ?emotion onyx:hasEmotionCategory ?category ;
           onyx:hasEmotionIntensity ?intensity .
  OPTIONAL { ?emotion onyx:algorithmConfidence ?confidence }

  OPTIONAL {
    ?targetEntity a oro:Robot .
    OPTIONAL { ?targetEntity oro:hasName ?robotName }
    BIND("robot" AS ?targetType)
    BIND(COALESCE(?robotName, STR(?targetEntity)) AS ?targetLabel)
  }
  OPTIONAL {
    ?targetEntity a prov:Person .
    OPTIONAL { ?targetEntity foaf:firstName ?personName }
    BIND("human" AS ?targetType)
    BIND(COALESCE(?personName, STR(?targetEntity)) AS ?targetLabel)
  }
  FILTER(BOUND(?targetType))
  BIND(xsd:double(STR(?intensity)) AS ?intensityValue)
  FILTER(BOUND(?intensityValue))
  FILTER (?intensityValue >= 0.75)
}
ORDER BY DESC(?intensityValue)
`,

  robotState: `
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX schema: <http://schema.org/>
PREFIX oro: <http://kb.openrobots.org#>

SELECT ?robot ?robotName ?t ?location
WHERE {
  ?state a prov:Entity ;
         prov:wasAttributedTo ?robot ;
         prov:generatedAtTime ?t ;
         schema:location ?location .
  OPTIONAL { ?robot oro:hasName ?robotName }
}
ORDER BY ?robot ?t
`,
}
