import * as d3 from 'd3'
import { useEffect, useRef } from 'react'
import { appColor } from '../utils/colors'

const DOMAIN_COLOR = '#7dd3fc'

function truncate(text, n = 26) {
  return text.length > n ? `${text.slice(0, n - 1)}…` : text
}

const LOCAL_IPS = new Set(['127.0.0.1', '::1', '0.0.0.0', '::'])

function isLocal(c) {
  return LOCAL_IPS.has(c.remote_ip) || c.remote_ip?.startsWith('127.')
}

/** Build app/domain nodes + deduped edges from raw connections. */
function buildModel(connections) {
  const nodes = new Map()
  const links = new Map()

  for (const c of connections) {
    if (!c.remote_ip || isLocal(c)) continue
    const appId = `a:${c.process}`
    const domId = `r:${c.remote_ip}`

    if (!nodes.has(appId)) {
      nodes.set(appId, {
        id: appId,
        kind: 'app',
        label: c.process,
        color: appColor(c.process),
        count: 0,
      })
    }
    nodes.get(appId).count += 1

    if (!nodes.has(domId)) {
      nodes.set(domId, {
        id: domId,
        kind: 'domain',
        label: c.domain || c.remote_ip,
        ip: c.remote_ip,
        color: DOMAIN_COLOR,
        count: 0,
      })
    }
    const dom = nodes.get(domId)
    dom.count += 1
    if (c.hostname) dom.label = c.hostname

    const key = `${appId}|${domId}`
    if (!links.has(key)) {
      links.set(key, {
        key,
        source: appId,
        target: domId,
        count: 0,
        color: appColor(c.process),
        protocol: c.protocol,
        port: c.remote_port,
      })
    }
    links.get(key).count += 1
  }

  return { nodes: [...nodes.values()], links: [...links.values()] }
}

function radiusOf(node) {
  return node.kind === 'app'
    ? Math.min(9 + node.count * 1.1, 20)
    : Math.min(5 + node.count * 0.9, 14)
}

export default function NetworkGraph({ connections, selected, onNodeClick }) {
  const containerRef = useRef(null)
  const apiRef = useRef(null)

  // ---------------------------------------------------------------- setup
  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    const svg = d3
      .select(container)
      .append('svg')
      .attr('class', 'h-full w-full')
      .style('cursor', 'grab')

    const root = svg.append('g')
    const linkLayer = root.append('g').attr('class', 'links')
    const nodeLayer = root.append('g').attr('class', 'nodes')

    let width = container.clientWidth || 800
    let height = container.clientHeight || 600

    const simulation = d3
      .forceSimulation()
      .force(
        'link',
        d3
          .forceLink()
          .id((d) => d.id)
          .distance((d) => (d.source?.kind === 'app' && d.target?.kind === 'domain' ? 130 : 90))
          .strength(0.65),
      )
      .force('charge', d3.forceManyBody().strength(-460))
      .force('collide', d3.forceCollide().radius((d) => radiusOf(d) + 26).iterations(2))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('x', d3.forceX(width / 2).strength(0.05))
      .force('y', d3.forceY(height / 2).strength(0.06))
      .on('tick', () => {
        linkLayer
          .selectAll('line')
          .attr('x1', (d) => d.source.x)
          .attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x)
          .attr('y2', (d) => d.target.y)

        nodeLayer
          .selectAll('g.node')
          .attr('transform', (d) => `translate(${d.x},${d.y})`)
      })

    const zoom = d3
      .zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => root.attr('transform', event.transform))

    svg.call(zoom).on('dblclick.zoom', null)
    svg.on('mousedown', () => svg.style('cursor', 'grabbing'))
    svg.on('mouseup', () => svg.style('cursor', 'grab'))

    const drag = d3
      .drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.alphaTarget(0.25).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        d.fx = null
        d.fy = null
      })

    const setHighlight = (activeId) => {
      if (!activeId) {
        linkLayer.selectAll('line').attr('stroke-opacity', 0.55)
        nodeLayer.selectAll('g.node').attr('opacity', 1)
        return
      }
      const active = new Set([activeId])
      linkLayer.selectAll('line').attr('stroke-opacity', (d) => {
        const s = typeof d.source === 'object' ? d.source.id : d.source
        const t = typeof d.target === 'object' ? d.target.id : d.target
        const on = s === activeId || t === activeId
        if (on) {
          active.add(s)
          active.add(t)
        }
        return on ? 0.9 : 0.06
      })
      nodeLayer
        .selectAll('g.node')
        .attr('opacity', (d) => (active.has(d.id) ? 1 : 0.18))
    }

    apiRef.current = { svg, root, linkLayer, nodeLayer, simulation, drag, setHighlight, width: () => width, height: () => height }

    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (!rect || rect.width < 10 || rect.height < 10) return
      width = rect.width
      height = rect.height
      simulation.force('center', d3.forceCenter(width / 2, height / 2))
      simulation.force('x', d3.forceX(width / 2).strength(0.05))
      simulation.force('y', d3.forceY(height / 2).strength(0.06))
      simulation.alpha(0.3).restart()
    })
    observer.observe(container)

    return () => {
      observer.disconnect()
      simulation.stop()
      svg.remove()
      apiRef.current = null
    }
  }, [])

  // ----------------------------------------------------------- data sync
  useEffect(() => {
    const api = apiRef.current
    if (!api) return
    const { linkLayer, nodeLayer, simulation, drag, setHighlight } = api

    const model = buildModel(connections)
    const prevNodes = new Map(
      simulation.nodes().map((n) => [n.id, n]),
    )

    // Reuse node objects so positions persist across updates.
    const nodes = model.nodes.map((spec) => {
      const prev = prevNodes.get(spec.id)
      if (prev) {
        Object.assign(prev, spec)
        return prev
      }
      const angle = Math.random() * Math.PI * 2
      const dist = 60 + Math.random() * 160
      return {
        ...spec,
        x: api.width() / 2 + Math.cos(angle) * dist,
        y: api.height() / 2 + Math.sin(angle) * dist,
      }
    })
    const links = model.links.map((l) => ({ ...l }))

    // ---- links
    const linkSel = linkLayer
      .selectAll('line')
      .data(links, (d) => d.key)
    linkSel
      .exit()
      .transition()
      .duration(350)
      .attr('stroke-opacity', 0)
      .remove()
    const linkEnter = linkSel
      .enter()
      .append('line')
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', (d) => 1.2 + d.count * 0.5)
      .attr('stroke-dasharray', '6 8')
      .attr('stroke-opacity', 0)
      .attr('class', 'edge-flow')
    linkEnter
      .transition()
      .duration(400)
      .attr('stroke-opacity', 0.55)
    linkLayer.selectAll('line').attr('stroke-width', (d) => 1.2 + d.count * 0.5)

    // ---- nodes
    const nodeSel = nodeLayer
      .selectAll('g.node')
      .data(nodes, (d) => d.id)
    nodeSel.exit().transition().duration(300).attr('opacity', 0).remove()

    const nodeEnter = nodeSel
      .enter()
      .append('g')
      .attr('class', (d) => `node node-${d.kind}`)
      .attr('opacity', 0)
      .style('cursor', 'pointer')
      .call(drag)
      .on('mouseenter', (_, d) => setHighlight(d.id))
      .on('mouseleave', () => setHighlight(null))
      .on('click', (event, d) => {
        event.stopPropagation()
        if (d.kind === 'app') onNodeClick?.(d.label)
      })

    nodeEnter
      .append('circle')
      .attr('r', (d) => radiusOf(d))
      .attr('fill', (d) => d.color)
      .attr('fill-opacity', 0.16)
      .attr('stroke', (d) => d.color)
      .attr('stroke-width', 1.6)
    nodeEnter
      .append('circle')
      .attr('r', (d) => Math.max(2.5, radiusOf(d) * 0.32))
      .attr('fill', (d) => d.color)
    nodeEnter
      .append('text')
      .attr('y', (d) => radiusOf(d) + 13)
      .attr('text-anchor', 'middle')
      .attr('font-size', (d) => (d.kind === 'app' ? 11 : 9.5))
      .attr('font-weight', (d) => (d.kind === 'app' ? 600 : 400))
      .attr('font-family', 'ui-monospace, SF Mono, monospace')
      .attr('fill', (d) => (d.kind === 'app' ? '#e2e8f0' : '#8fb3d0'))
      .attr('paint-order', 'stroke')
      .attr('stroke', '#070b12')
      .attr('stroke-width', 3)
      .text((d) => truncate(d.label))
    nodeEnter.append('title').text(
      (d) =>
        `${d.label}\n${d.kind === 'app' ? 'application' : d.ip}\n${d.count} connection${d.count > 1 ? 's' : ''}`,
    )
    nodeEnter.transition().duration(450).attr('opacity', 1)

    // keep radii/labels fresh on reused nodes
    nodeLayer.selectAll('g.node').each(function refresh(d) {
      const g = d3.select(this)
      g.select('circle').transition().duration(300).attr('r', radiusOf(d))
      g.select('text').attr('y', radiusOf(d) + 13).text(truncate(d.label))
      g.select('title').text(
        `${d.label}\n${d.kind === 'app' ? 'application' : d.ip}\n${d.count} connection${d.count > 1 ? 's' : ''}`,
      )
    })

    // selection ring for the focused application
    nodeLayer
      .selectAll('g.node')
      .select('circle')
      .attr('stroke-width', (d) => (selected && d.id === `a:${selected}` ? 3.2 : 1.6))

    simulation.nodes(nodes)
    simulation.force('link').links(links)
    simulation.alpha(0.6).restart()
  }, [connections, selected, onNodeClick])

  const hasRemote = connections.some((c) => c.remote_ip && !isLocal(c))

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="absolute inset-0" />
      {!hasRemote && (
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-2 text-center">
          <div className="text-sm text-slate-500">No outbound connections yet</div>
          <div className="text-xs text-slate-600">
            Open a browser or wait for background apps to phone home
          </div>
        </div>
      )}
      <div className="pointer-events-none absolute bottom-3 left-3 flex gap-4 text-[10px] text-slate-500">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full border border-cyan-400 bg-cyan-400/20" />
          application
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full border border-sky-300 bg-sky-300/20" />
          domain / ip
        </span>
        <span className="hidden sm:inline">scroll to zoom · drag to pan · click app to focus</span>
      </div>
    </div>
  )
}
