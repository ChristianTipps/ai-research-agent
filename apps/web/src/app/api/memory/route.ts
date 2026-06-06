import { listMemory } from "@/lib/backend";
import { NextResponse } from "next/server";

export async function GET() {
  const memory = await listMemory();
  return NextResponse.json(memory);
}
