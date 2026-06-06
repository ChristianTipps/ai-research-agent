import { getMemoryDocument } from "@/lib/backend";
import { NextResponse } from "next/server";

export async function GET(_: Request, context: { params: Promise<{ key: string[] }> }) {
  const { key } = await context.params;
  const document = await getMemoryDocument(key.join("/"));
  return NextResponse.json(document);
}
