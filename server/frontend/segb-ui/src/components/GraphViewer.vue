<template>
    <div ref="container" style="height:700px"></div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { DataSet, Network } from 'vis-network/standalone'
import { Parser } from 'n3'


const props = defineProps({ ttl: { type: String, required: true } })
const container = ref(null)
let network


function shorten(uri) {
    if (!uri) return ''
    const s = String(uri)
    return s.includes('#') ? s.split('#').pop() : s.split('/').pop()
}



function parseTTLAsync(ttl) {
    return new Promise((resolve, reject) => {
        const nodes = new Map()
        const edges = []
        const parser = new Parser()

        parser.parse(ttl, (error, quad) => {
            if (error) return reject(error)
            if (!quad) return resolve({ nodes, edges })

            const s = String(quad.subject.value)
            const p = String(quad.predicate.value)
            const o = quad.object.termType === 'Literal' ? '"' + quad.object.value + '"' : String(quad.object.value)

            if (!nodes.has(s)) nodes.set(s, { id: s, label: s })
            if (!nodes.has(o)) nodes.set(o, { id: o, label: o })
            edges.push({ from: s, to: o, label: p })
        })
    })
}


async function buildGraph(ttl) {

    const {nodes, edges} = await parseTTLAsync(ttl)

    const data = {
        nodes: new DataSet([...nodes.values()]),
        edges: new DataSet(edges),
    }
    
    const opts = {
        layout: { improvedLayout: true },
        physics: { solver: 'forceAtlas2Based', stabilization: true },
        edges: { smooth: { type: 'dynamic' } },
        interaction: { hover: true, navigationButtons: true, keyboard: true }
    }
    if (network) network.destroy()
    network = new Network(container.value, data, opts)
    console.log('Graph built with', nodes.size, 'nodes and', edges.length, 'edges.')
}


onMounted(() => buildGraph(props.ttl))
watch(() => props.ttl, (v) => buildGraph(v))
</script>