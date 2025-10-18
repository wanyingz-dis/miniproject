import { useEffect, useRef } from "react";
import * as d3 from "d3";
import type { DailyCost } from "../../types";

type Props = {
    data: DailyCost[];
    onBarClick?: (date: string) => void;
    height?: number;
};

export default function DailyCostChart({ data, onBarClick, height = 320 }: Props) {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const svgRef = useRef<SVGSVGElement | null>(null);
    const tooltipRef = useRef<HTMLDivElement | null>(null);

    useEffect(() => {
        if (!containerRef.current) return;

        const ro = new ResizeObserver((entries) => {
            for (const entry of entries) {
                const width = Math.floor(entry.contentRect.width);
                render(width, height);
            }
        });
        ro.observe(containerRef.current);
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
        const margin = { top: 8, right: 16, bottom: 28, left: 48 };
        const iw = Math.max(0, width - margin.left - margin.right);
        const ih = Math.max(0, height - margin.top - margin.bottom);

        const svg = d3.select(svgRef.current!).attr("width", width).attr("height", height);
        svg.selectAll("*").remove();

        const g = svg.append("g").attr("transform", `translate(${margin.left},${margin.top})`);

        // Parse dates
        const parsed = data.map((d) => ({
            ...d,
            dateObj: d3.utcParse("%Y-%m-%d")(d.date) ?? new Date(d.date),
        }));

        // Scales
        const x = d3
            .scaleBand<Date>()
            .domain(parsed.map((d) => d.dateObj))
            .range([0, iw])
            .padding(0.2);

        const y = d3
            .scaleLinear()
            .domain([0, d3.max(parsed, (d) => d.total_cost)! * 1.1 || 1])
            .nice()
            .range([ih, 0]);

        // Axes
        const xAxis = d3.axisBottom<Date>(x).tickFormat((d) => d3.timeFormat("%m-%d")(d));
        const yAxis = d3.axisLeft(y).ticks(6).tickFormat((d) => `$${Number(d).toFixed(0)}`);

        g.append("g").attr("transform", `translate(0,${ih})`).call(xAxis as any);
        g.append("g").call(yAxis as any);

        const tooltip = d3.select(tooltipRef.current!);

        // Bars
        g.selectAll("rect.bar")
            .data(parsed, (d: any) => d.date)
            .join("rect")
            .attr("class", "bar")
            .attr("x", (d) => x(d.dateObj)!)
            .attr("y", ih)
            .attr("width", x.bandwidth())
            .attr("height", 0)
            .attr("fill", "#4f46e5")
            .style("cursor", "pointer")
            .on("pointerenter", function () {
                d3.select(this).transition().duration(150).attr("fill", "#4338ca");
            })
            .on("pointermove", function (event, d) {
                const html = `
          <div class="font-medium">${d.date}</div>
          <div>Cost: $${d.total_cost.toFixed(2)}</div>
          <div>Runs: ${d.run_count} | Experiments: ${d.experiment_count}</div>
        `;
                tooltip
                    .html(html)
                    .style("opacity", 1)
                    .style("left", `${event.offsetX + 16}px`)
                    .style("top", `${event.offsetY + 16}px`);
            })
            .on("pointerleave", function () {
                d3.select(this).transition().duration(150).attr("fill", "#4f46e5");
                tooltip.style("opacity", 0);
            })
            .on("click", (_event, d) => onBarClick?.(d.date))
            .transition()
            .duration(400)
            .attr("y", (d) => y(d.total_cost))
            .attr("height", (d) => ih - y(d.total_cost));

        // Trend line: simple moving average (window=5)
        const windowSize = 5;
        const sma = parsed.map((_, i) => {
            const start = Math.max(0, i - windowSize + 1);
            const slice = parsed.slice(start, i + 1);
            const avg = d3.mean(slice, (s) => s.total_cost) ?? 0;
            return { dateObj: parsed[i].dateObj, value: avg };
        });

        const line = d3
            .line<{ dateObj: Date; value: number }>()
            .x((d) => x(d.dateObj)! + x.bandwidth() / 2)
            .y((d) => y(d.value))
            .curve(d3.curveMonotoneX);

        g.append("path")
            .datum(sma)
            .attr("fill", "none")
            .attr("stroke", "#111827")
            .attr("stroke-opacity", 0.6)
            .attr("stroke-width", 2)
            .attr("d", line as any);
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
