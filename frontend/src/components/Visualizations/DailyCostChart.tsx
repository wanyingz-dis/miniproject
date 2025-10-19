import { useEffect, useMemo, useRef } from "react";
import * as d3 from "d3";

type Point = { date: string; total_cost: number; run_count?: number; experiment_count?: number };

function movingAverage(arr: number[], window = 7) {
    const out: number[] = [];
    for (let i = 0; i < arr.length; i++) {
        const start = Math.max(0, i - window + 1);
        const slice = arr.slice(start, i + 1);
        out.push(d3.mean(slice) ?? 0);
    }
    return out;
}

export default function DailyCostChart({
    data,
    onBarClick,
    width = 520,
    height = 360,
}: {
    data: Point[];
    onBarClick?: (isoDate: string) => void;
    width?: number;
    height?: number;
}) {
    const svgRef = useRef<SVGSVGElement | null>(null);

    const parsed = useMemo(
        () =>
            data.map((d) => ({
                ...d,
                dateObj: new Date(d.date),
            })),
        [data]
    );

    useEffect(() => {
        if (!parsed.length) return;

        const m = { top: 24, right: 16, bottom: 36, left: 56 };
        const w = width - m.left - m.right;
        const h = height - m.top - m.bottom;

        const x = d3
            .scaleBand<Date>()
            .domain(parsed.map((d) => d.dateObj))
            .range([0, w])
            .padding(0.2);

        const y = d3
            .scaleLinear()
            .domain([0, d3.max(parsed, (d) => d.total_cost)! * 1.1])
            .nice()
            .range([h, 0]);

        const costSeries = parsed.map((d) => d.total_cost);
        const ma7 = movingAverage(costSeries, 7);

        const svg = d3.select(svgRef.current!).attr("width", width).attr("height", height);
        svg.selectAll("*").remove();

        const g = svg.append("g").attr("transform", `translate(${m.left},${m.top})`);

        g.append("g").attr("transform", `translate(0,${h})`).call(
            d3.axisBottom(x)
                .tickFormat((d) => d3.timeFormat("%b %d")(d as Date))  // Better date display eg. "Oct 12" format
                .tickValues(x.domain().filter((_, i) => i % Math.max(1, Math.floor(parsed.length / 6)) === 0))  // Show fewer ticks
        );

        g.append("g").call(d3.axisLeft(y).ticks(5).tickFormat((v) => `$${Number(v).toFixed(0)}` as any));

        const tooltip = d3
            .select(svgRef.current!.parentElement)
            .append("div")
            .style("position", "absolute")
            .style("pointer-events", "none")
            .style("background", "white")
            .style("border", "1px solid #e5e7eb")
            .style("padding", "8px 10px")
            .style("border-radius", "6px")
            .style("font-size", "12px")
            .style("box-shadow", "0 6px 14px rgba(0,0,0,.08)")
            .style("opacity", 0);

        // bars
        g.selectAll("rect.bar")
            .data(parsed)
            .enter()
            .append("rect")
            .attr("class", "bar")
            .attr("x", (d) => x(d.dateObj)!)
            .attr("y", (d) => y(d.total_cost))
            .attr("width", x.bandwidth())
            .attr("height", (d) => h - y(d.total_cost))
            .attr("fill", "#4f46e5")
            .style("cursor", "pointer")
            .on("mouseenter", function (_e, d) {
                d3.select(this).attr("fill", "#4338ca");
                tooltip
                    .style("opacity", 1)
                    .html(
                        `<div style="font-weight:600;margin-bottom:4px">${d3.timeFormat("yyyy-MM-dd")(d.dateObj)}</div>
             <div>Cost: $${d.total_cost.toFixed(2)}</div>
             ${d.run_count != null ? `<div>Runs: ${d.run_count}</div>` : ""}
             ${d.experiment_count != null ? `<div>Experiments: ${d.experiment_count}</div>` : ""}`
                    );
            })
            .on("mousemove", function (event) {
                tooltip.style("left", event.offsetX + 16 + "px").style("top", event.offsetY + 16 + "px");
            })
            .on("mouseleave", function () {
                d3.select(this).attr("fill", "#4f46e5");
                tooltip.style("opacity", 0);
            })
            .on("click", (_e, d) => onBarClick?.(d.date));

        // moving average line
        const line = d3
            .line<[Date, number]>()
            .x((d) => x(d[0])! + x.bandwidth() / 2)
            .y((d) => y(d[1]))
            .curve(d3.curveMonotoneX);

        const pairs: [Date, number][] = parsed.map((d, i) => [d.dateObj, ma7[i]]);
        g.append("path")
            .attr("fill", "none")
            .attr("stroke", "#6b7280")
            .attr("stroke-width", 2)
            .attr("d", line(pairs)!);

        return () => tooltip.remove();
    }, [parsed, width, height, onBarClick]);

    return <svg ref={svgRef} />;
}
