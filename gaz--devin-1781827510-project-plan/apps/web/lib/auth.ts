import { cookies } from "next/headers";
export type CoreTokenPairResponse = {
  access_token: string;
  refresh_token: string;
  access_expires_at: number | string;
  refresh_expires_at: number | string;
  requires_mfa?: boolean;
};

const ACCESS_TOKEN_COOKIE = "cf_access_token";
const REFRESH_TOKEN_COOKIE = "cf_refresh_token";
const MFA_TOKEN_COOKIE = "cf_mfa_token";
const MFA_SETUP_COOKIE = "cf_mfa_setup";
const MFA_RECOVERY_CODES_COOKIE = "cf_mfa_recovery_codes";

export type MfaSetupPayload = {
  provisioning_uri: string;
  secret: string;
};

export type MfaRecoveryCodesPayload = {
  codes: string[];
};

export async function setAuthCookies(tokens: CoreTokenPairResponse) {
  const cookieStore = await cookies();

  cookieStore.set(ACCESS_TOKEN_COOKIE, tokens.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: new Date(tokens.access_expires_at),
    path: "/",
  });

  cookieStore.set(REFRESH_TOKEN_COOKIE, tokens.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: new Date(tokens.refresh_expires_at),
    path: "/",
  });
}

export async function getAccessToken() {
  const cookieStore = await cookies();
  return cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;
}

export async function getRefreshToken() {
  const cookieStore = await cookies();
  return cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;
}

export async function clearAuthCookies() {
  const cookieStore = await cookies();
  cookieStore.delete(ACCESS_TOKEN_COOKIE);
  cookieStore.delete(REFRESH_TOKEN_COOKIE);
  cookieStore.delete(MFA_TOKEN_COOKIE);
  cookieStore.delete(MFA_SETUP_COOKIE);
  cookieStore.delete(MFA_RECOVERY_CODES_COOKIE);
}

export async function setMfaToken(token: string, expires_at: number | string) {
  const cookieStore = await cookies();
  cookieStore.set(MFA_TOKEN_COOKIE, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    expires: new Date(expires_at),
    path: "/",
  });
}

export async function getMfaToken() {
  const cookieStore = await cookies();
  return cookieStore.get(MFA_TOKEN_COOKIE)?.value;
}

export async function clearMfaToken() {
  const cookieStore = await cookies();
  cookieStore.delete(MFA_TOKEN_COOKIE);
}

export async function setMfaSetup(payload: MfaSetupPayload) {
  const cookieStore = await cookies();
  const encodedPayload = Buffer.from(JSON.stringify(payload), "utf8").toString("base64url");

  cookieStore.set(MFA_SETUP_COOKIE, encodedPayload, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 10 * 60,
    path: "/",
  });
}

export async function getMfaSetup() {
  const cookieStore = await cookies();
  const value = cookieStore.get(MFA_SETUP_COOKIE)?.value;

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(Buffer.from(value, "base64url").toString("utf8")) as MfaSetupPayload;
  } catch {
    return null;
  }
}

export async function clearMfaSetup() {
  const cookieStore = await cookies();
  cookieStore.delete(MFA_SETUP_COOKIE);
}

export async function setMfaRecoveryCodes(codes: string[]) {
  const cookieStore = await cookies();
  const encodedPayload = Buffer.from(JSON.stringify({ codes }), "utf8").toString("base64url");

  cookieStore.set(MFA_RECOVERY_CODES_COOKIE, encodedPayload, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 10 * 60,
    path: "/",
  });
}

export async function getMfaRecoveryCodes() {
  const cookieStore = await cookies();
  const value = cookieStore.get(MFA_RECOVERY_CODES_COOKIE)?.value;

  if (!value) {
    return null;
  }

  try {
    return JSON.parse(Buffer.from(value, "base64url").toString("utf8")) as MfaRecoveryCodesPayload;
  } catch {
    return null;
  }
}

export async function clearMfaRecoveryCodes() {
  const cookieStore = await cookies();
  cookieStore.delete(MFA_RECOVERY_CODES_COOKIE);
}
