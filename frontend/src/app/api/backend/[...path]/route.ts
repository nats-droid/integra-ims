import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000'

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params
  const pathStr = path.join('/')
  const url = new URL(req.url)
  const targetUrl = `${BACKEND_URL}/${pathStr}${url.search}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const auth = req.headers.get('Authorization')
  if (auth) headers['Authorization'] = auth

  const body =
    req.method !== 'GET' && req.method !== 'HEAD'
      ? await req.text()
      : undefined

  const res = await fetch(targetUrl, {
    method: req.method,
    headers,
    body,
  })

  const data = await res.text()
  return new NextResponse(data, {
    status: res.status,
    headers: {
      'Content-Type':
        res.headers.get('Content-Type') || 'application/json',
    },
  })
}

export const GET = handler
export const POST = handler
export const PUT = handler
export const DELETE = handler
export const PATCH = handler
