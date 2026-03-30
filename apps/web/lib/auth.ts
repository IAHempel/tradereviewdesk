import { auth, currentUser } from "@clerk/nextjs/server";
import { createHmac } from "node:crypto";

import { NextResponse } from "next/server";

const DEMO_EMAIL = "trader@example.com";
const DEMO_DISPLAY_NAME = "Jordan";
const LOCAL_DEMO_AUTH_PROVIDER_ID = "local-demo-user";
const AUTH_MODE = process.env.AUTH_MODE ?? "disabled";
const AUTH_SHARED_SECRET = process.env.AUTH_INTERNAL_SHARED_SECRET ?? "replace-me";
const APP_ENV = process.env.APP_ENV ?? process.env.NODE_ENV ?? "development";

export type ServerUserContext = {
  authProvider: "clerk" | "local";
  authProviderUserId: string;
  authProviderId: string;
  email: string;
  displayName: string | null;
};

export class RouteAuthError extends Error {
  constructor(message = "Authentication required.") {
    super(message);
    this.name = "RouteAuthError";
  }
}

export function isClerkAuthEnabled(): boolean {
  return AUTH_MODE === "clerk";
}

function isProductionEnvironment(): boolean {
  return APP_ENV === "production";
}

function isAuthConfigured(): boolean {
  return isClerkAuthEnabled() && AUTH_SHARED_SECRET !== "replace-me";
}

function getDemoUserContext(): ServerUserContext {
  return {
    authProvider: "local",
    authProviderUserId: LOCAL_DEMO_AUTH_PROVIDER_ID,
    authProviderId: `local:${LOCAL_DEMO_AUTH_PROVIDER_ID}`,
    email: DEMO_EMAIL,
    displayName: DEMO_DISPLAY_NAME,
  };
}

export async function getServerUserContext(): Promise<ServerUserContext | null> {
  if (isProductionEnvironment() && !isAuthConfigured()) {
    return null;
  }

  if (!isClerkAuthEnabled()) {
    return getDemoUserContext();
  }

  const { userId } = await auth();
  if (!userId) {
    return null;
  }

  const user = await currentUser();
  if (!user) {
    return null;
  }

  const primaryEmail =
    user.primaryEmailAddress?.emailAddress ??
    user.emailAddresses.find((emailAddress) => emailAddress.id === user.primaryEmailAddressId)?.emailAddress ??
    user.emailAddresses[0]?.emailAddress;

  if (!primaryEmail) {
    return null;
  }

  return {
    authProvider: "clerk",
    authProviderUserId: userId,
    authProviderId: `clerk:${userId}`,
    email: primaryEmail,
    displayName: user.fullName ?? ([user.firstName, user.lastName].filter(Boolean).join(" ") || null),
  };
}

export async function requireServerUserContext(): Promise<ServerUserContext> {
  const userContext = await getServerUserContext();
  if (!userContext) {
    throw new RouteAuthError();
  }

  return userContext;
}

export async function getRouteAuthFailureResponse(): Promise<NextResponse | null> {
  if (isProductionEnvironment() && !isAuthConfigured()) {
    return NextResponse.json({ message: "Authentication is not configured for production." }, { status: 503 });
  }

  if (!isClerkAuthEnabled()) {
    return null;
  }

  const userContext = await getServerUserContext();
  if (userContext) {
    return null;
  }

  return NextResponse.json({ message: "Authentication required." }, { status: 401 });
}

function buildAuthSignature(userContext: ServerUserContext, timestamp: string): string {
  if (isProductionEnvironment() && AUTH_SHARED_SECRET === "replace-me") {
    throw new RouteAuthError("Authentication secret is not configured for production.");
  }

  const payload = [
    userContext.authProvider,
    userContext.authProviderUserId,
    userContext.email,
    userContext.displayName ?? "",
    timestamp,
  ].join("\n");

  return createHmac("sha256", AUTH_SHARED_SECRET).update(payload).digest("hex");
}

export async function buildInternalAuthHeaders(): Promise<Headers> {
  const userContext = await requireServerUserContext();
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const headers = new Headers();

  headers.set("X-TradeNOC-Auth-Provider", userContext.authProvider);
  headers.set("X-TradeNOC-Auth-User-Id", userContext.authProviderUserId);
  headers.set("X-TradeNOC-Auth-Email", userContext.email);
  headers.set("X-TradeNOC-Auth-Display-Name", userContext.displayName ?? "");
  headers.set("X-TradeNOC-Auth-Timestamp", timestamp);
  headers.set("X-TradeNOC-Auth-Signature", buildAuthSignature(userContext, timestamp));

  return headers;
}
