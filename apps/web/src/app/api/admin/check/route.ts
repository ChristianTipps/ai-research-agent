import { BackendRequestError, checkAdminPasscode } from "@/lib/backend";
import { NextResponse } from "next/server";
import { z } from "zod";

const adminCheckSchema = z.object({
  passcode: z.string().optional(),
});

export async function POST(request: Request) {
  const json = await request.json();
  const parsed = adminCheckSchema.safeParse(json);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid admin passcode check request." }, { status: 400 });
  }

  try {
    const response = await checkAdminPasscode(parsed.data.passcode);
    return NextResponse.json(response);
  } catch (error) {
    if (error instanceof BackendRequestError) {
      return NextResponse.json(error.payload, { status: error.status });
    }
    throw error;
  }
}
