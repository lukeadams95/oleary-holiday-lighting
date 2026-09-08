interface Env {
  RESEND_API_KEY: string;
}

interface PagesContext {
  request: Request;
  env: Env;
}

const RESEND_API_URL = "https://api.resend.com/emails";
const FROM_ADDRESS = "O'Leary Holiday Lighting <leads@newleadrelay.com>";
const TO_ADDRESSES = ["olearylighting@gmail.com"];

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...CORS_HEADERS },
  });
}

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function labelFor(key: string): string {
  return key
    .replace(/[_-]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function buildEmailHtml(fields: Record<string, unknown>): string {
  const name = String(fields.name ?? "").trim() || "New lead";
  const email = String(fields.email ?? "").trim();
  const phone = String(fields.phone ?? "").trim();

  const contactLinks = [
    email
      ? `<a href="mailto:${escapeHtml(email)}" style="display:block;color:#ffffff;font-size:18px;font-weight:600;line-height:1.6;text-decoration:underline;">${escapeHtml(email)}</a>`
      : "",
    phone
      ? `<a href="tel:${escapeHtml(phone.replace(/[^\d+]/g, ""))}" style="display:block;color:#ffffff;font-size:18px;font-weight:600;line-height:1.6;text-decoration:underline;">${escapeHtml(phone)}</a>`
      : "",
  ]
    .filter(Boolean)
    .join("");

  const rows = Object.entries(fields)
    .filter(([, value]) => {
      if (Array.isArray(value)) return value.length > 0;
      return value !== undefined && value !== null && String(value).trim() !== "";
    })
    .map(([key, value]) => {
      const display = Array.isArray(value) ? value.join(", ") : String(value);
      return `<tr>
        <td style="padding:10px 14px;border:1px solid #EAE6E1;background:#FAF7F4;font-weight:600;color:#1A1A1A;white-space:nowrap;font-family:Arial,Helvetica,sans-serif;font-size:14px;vertical-align:top;">${escapeHtml(labelFor(key))}</td>
        <td style="padding:10px 14px;border:1px solid #EAE6E1;color:#1A1A1A;font-family:Arial,Helvetica,sans-serif;font-size:14px;">${escapeHtml(display)}</td>
      </tr>`;
    })
    .join("");

  return `<div style="font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:0 auto;">
  <div style="background:#C8102E;padding:24px 20px;border-radius:8px 8px 0 0;">
    <p style="margin:0 0 8px;color:#FBD9DE;font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Contact This Lead</p>
    <p style="margin:0 0 10px;color:#ffffff;font-size:22px;font-weight:700;">${escapeHtml(name)}</p>
    ${contactLinks}
  </div>
  <table style="width:100%;border-collapse:collapse;margin-top:20px;">
    ${rows}
  </table>
</div>`;
}

async function parseFields(request: Request): Promise<Record<string, unknown>> {
  const contentType = request.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const body = await request.json();
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      throw new Error("Request body must be a JSON object");
    }
    return body as Record<string, unknown>;
  }

  const form = await request.formData();
  const fields: Record<string, unknown> = {};
  for (const key of new Set(form.keys())) {
    const values = form.getAll(key).map((v) => (typeof v === "string" ? v : v.name));
    fields[key] = values.length > 1 ? values : values[0];
  }
  return fields;
}

export async function onRequestOptions(): Promise<Response> {
  return new Response(null, { status: 204, headers: CORS_HEADERS });
}

export async function onRequestPost(context: PagesContext): Promise<Response> {
  const { request, env } = context;

  const apiKey = env.RESEND_API_KEY;
  if (!apiKey) {
    console.error("send-lead-notification: RESEND_API_KEY is not configured");
    return jsonResponse({ error: "Email is not configured" }, 500);
  }

  let fields: Record<string, unknown>;
  try {
    fields = await parseFields(request);
  } catch (err) {
    return jsonResponse({ error: "Invalid form data" }, 400);
  }

  const name = String(fields.name ?? "").trim();
  if (!name) {
    return jsonResponse({ error: "Missing required field: name" }, 400);
  }
  const email = String(fields.email ?? "").trim();

  try {
    const resendRes = await fetch(RESEND_API_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: FROM_ADDRESS,
        to: TO_ADDRESSES,
        ...(email ? { reply_to: email } : {}),
        subject: `New Lead - ${name}`,
        html: buildEmailHtml(fields),
      }),
    });

    if (!resendRes.ok) {
      const detail = await resendRes.text();
      console.error("send-lead-notification: Resend API error", resendRes.status, detail);
      return jsonResponse({ error: "Failed to send email" }, 502);
    }

    return jsonResponse({ success: true }, 200);
  } catch (err) {
    console.error("send-lead-notification: unexpected error", err);
    return jsonResponse({ error: "Unexpected error" }, 500);
  }
}
