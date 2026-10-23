import { ObjectId } from "mongodb";
import { auth } from "@/auth";
import { getAvatarsCollection } from "@/lib/db";

/** Serves an uploaded profile picture to signed-in users. */
export async function GET(_request: Request, { params }: { params: Promise<{ userId: string }> }) {
  if (!(await auth())?.user) return new Response(null, { status: 401 });

  const { userId } = await params;
  if (!ObjectId.isValid(userId)) return new Response(null, { status: 404 });

  const avatars = await getAvatarsCollection();
  const avatar = await avatars.findOne({ _id: new ObjectId(userId) });
  if (!avatar) return new Response(null, { status: 404 });

  return new Response(new Uint8Array(avatar.data.buffer), {
    headers: {
      // Only types verified by sniffImageType at upload are ever stored.
      "Content-Type": avatar.contentType,
      "Content-Length": String(avatar.size),
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; sandbox",
      "Content-Disposition": "inline",
      // URLs carry ?v=<updatedAt>, so a new upload gets a new URL.
      "Cache-Control": "private, max-age=31536000, immutable",
    },
  });
}
