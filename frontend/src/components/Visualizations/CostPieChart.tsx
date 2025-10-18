import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { CostByExperiment } from "../../types";

type Props = {
    data: CostByExperiment[];
    onSliceClick?: (experimentId: number) => void;
    height?: number;
};

export default function CostPieChart({ data, onSliceClick, height = 320 }: Props) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const svgRef = useRef<SVGSVGElement | null>(null);
    const tooltipRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        const container = containerRef.current;
        const svg = d3.select(svgRef.current!);
        const tooltip = d3.select(tooltipRef.current!);

        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const width = Math.floor(entry.contentRect.width);
                render(width, height);
            }
        });
        ro.observe(container);

        return () => ro.disconnect();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    useEffect(() => {
        if (!containerRef.current) return;
        const width = Math.floor(containerRef.current.clientWidth || 600);
        render(width, height);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [data, height]);

    function render(width: number, height: number) {
        const margin = 12;
        const r = Math.min(width, height) / 2 - margin;

        const svg = d3
            .select(svgRef.current!)
            .attr("width", width)
            .attr("height", height);

        svg.selectAll("*").remove();

        const g = svg
            .append("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

        const color = d3.scaleOrdinal<string>()
            .domain(data.map(d => String(d.experiment_id)))
            .range(d3.schemeTableau10 as readonly string[]);

        const pie = d3
            .pie<CostByExperiment>()
            .value((d) => d.total_cost)
            .sort(null);

        const arcs = pie(data);

        const arcGen = d3.arc<d3.PieArcDatum<CostByExperiment>>()
            .innerRadius(0)
            .outerRadius(r);

        const arcGenHover = d3.arc<d3.PieArcDatum<CostByExperiment>>()
            .innerRadius(0)
            .outerRadius(r + 10);

        const paths = g
            .selectAll("path.slice")
            .data(arcs, (d: any) => d.data.experiment_id)
            .join("path")
            .attr("class", "slice")
            .attr("fill", (d) => color(String(d.data.experiment_id)) as string)
            .attr("d", arcGen as any)
            .style("cursor", "pointer")
            .on("pointerenter", function (event, d) {
                d3.select(this).transition().duration(150).attr("d", arcGenHover as any);
                showTooltip(event, d);
            })
            .on("pointermove", function (event, d) {
                showTooltip(event, d);
            })
            .on("pointerleave", function () {
                d3.select(this).transition().duration(150).attr("d", arcGen as any);
                hideTooltip();
            })
            .on("click", (_event, d) => {
                onSliceClick?.(d.data.experiment_id);
            });

        // Labels (optional)
        const labelArc = d3.arc<d3.PieArcDatum<CostByExperiment>>()
            .innerRadius(r * 0.6)
            .outerRadius(r * 0.6);

        g.selectAll("text.label")
            .data(arcs)
            .join("text")
            .attr("class", "text-xs fill-gray-700")
            .attr("transform", (d) => `translate(${labelArc.centroid(d)})`)
            .attr("text-anchor", "middle")
            .text((d) => d.data.experiment_name)
            .style("pointer-events", "none");

        function showTooltip(event: PointerEvent, d: d3.PieArcDatum<CostByExperiment>) {
            const html = `
        <div class="font-medium">${d.data.experiment_name}</div>
        <div>Total cost: $${d.data.total_cost.toFixed(2)}</div>
        <div>Runs: ${d.data.run_count}</div>
        <div>Share: ${d.data.percentage.toFixed(1)}%</div>
      `;
            tooltip
                .html(html)
                .style("opacity", 1)
                .style("left", `${event.offsetX + 16}px`)
                .style("top", `${event.offsetY + 16}px`);
        }
        function hideTooltip() {
            tooltip.style("opacity", 0);
        }
    }

    return (
        <div ref={containerRef} className="relative w-full" style={{ height }}>
            <svg ref={svgRef} />
            <div
                ref={tooltipRef}
                className="pointer-events-none absolute z-10 rounded bg-white/90 px-3 py-2 text-sm shadow border border-gray-200"
                style={{ opacity: 0 }}
            />
        </div>
    );
}
