import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {
};

export default process.env.NEXT_PUBLIC_SENTRY_DSN ? withSentryConfig(nextConfig, {
  silent: true,
  org: "callforce",
  project: "callforce-web",
}) : nextConfig;
