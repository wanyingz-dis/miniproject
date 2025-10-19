import { useEffect, useRef } from "react";
import * as d3 from "d3";

type Slice = {
    experiment_id: number;
    experiment_name: string;
    total_cost: number;
    percentage?: number;
    run_count?: number;
};

export default function CostPieChart({
    data,
    onSliceClick,
    width = 520,
    height = 360,
}: {
    data: Slice[];
    onSliceClick?: (id: number) => void;
    width?: number;
    height?: number;
}) {
    const svgRef = useRef<SVGSVGElement | null>(null);

    useEffect(() => {
        if (!data?.length) return;

        const radius = Math.min(width, height) / 2;
        const arc = d3.arc<d3.PieArcDatum<Slice>>().innerRadius(0).outerRadius(radius - 8);
        const arcHover = d3.arc<d3.PieArcDatum<Slice>>().innerRadius(0).outerRadius(radius + 8);

        const pie = d3
            .pie<Slice>()
            .value((d) => d.total_cost)
            .sort(null);

        const color = d3.scaleOrdinal<string>().range(d3.schemeTableau10 as unknown as string[]);

        // cleanup then draw
        const svg = d3
            .select(svgRef.current!)
            .attr("width", width)
            .attr("height", height);
        svg.selectAll("*").remove();

        const g = svg
            .append("g")
            .attr("transform", `translate(${width / 2},${height / 2})`);

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

        const arcs = g
            .selectAll("path")
            .data(pie(data))
            .enter()
            .append("path")
            .attr("fill", (d, i) => color(String(i)))
            .attr("d", arc)
            .style("cursor", "pointer")
            .on("mouseenter", function (event, d) {
                d3.select(this).transition().duration(150).attr("d", arcHover(d));
                const pct = d.data.percentage ?? (d.data.total_cost / d3.sum(data, (x) => x.total_cost)) * 100;
                tooltip
                    .style("opacity", 1)
                    .html(
                        `<div style="font-weight:600;margin-bottom:4px">${d.data.experiment_name}</div>
             <div>Cost: $${d.data.total_cost.toFixed(2)}</div>
             <div>Share: ${pct.toFixed(1)}%</div>
             ${d.data.run_count != null ? `<div>Runs: ${d.data.run_count}</div>` : ""}`
                    );
            })
            .on("mousemove", function (event) {
                tooltip.style("left", event.offsetX + 16 + "px").style("top", event.offsetY + 16 + "px");
            })
            .on("mouseleave", function (_event, d) {
                d3.select(this).transition().duration(150).attr("d", arc(d));
                tooltip.style("opacity", 0);
            })
            .on("click", (_event, d) => {
                onSliceClick?.(d.data.experiment_id);
            });

        // labels（avoid too much hiding, only display the max 3）
        const top = [...data].sort((a, b) => b.total_cost - a.total_cost).slice(0, 3);
        const showIds = new Set(top.map((t) => t.experiment_id));

        g.selectAll("text.label")
            .data(pie(data).filter((d) => showIds.has(d.data.experiment_id)))
            .enter()
            .append("text")
            .attr("class", "label")
            .attr("transform", (d) => `translate(${arc.centroid(d)})`)
            .attr("dy", "0.35em")
            .attr("text-anchor", "middle")
            .style("font-size", "12px")
            .style("fill", "#111827")
            .text((d) => d.data.experiment_name);

        return () => {
            tooltip.remove();
        };
    }, [data, height, width, onSliceClick]);

    return <svg ref={svgRef} />;
}
