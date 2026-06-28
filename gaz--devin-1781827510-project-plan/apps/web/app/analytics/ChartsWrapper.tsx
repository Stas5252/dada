"use client";

import dynamic from "next/dynamic";

export const MiniBarChart = dynamic(() => import("./AnalyticsCharts").then((mod) => mod.MiniBarChart), { ssr: false });
export const ChannelList = dynamic(() => import("./AnalyticsCharts").then((mod) => mod.ChannelList), { ssr: false });
