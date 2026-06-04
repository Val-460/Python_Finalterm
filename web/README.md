Deploy the `web/` folder to Vercel (Next.js). Set environment variable `NEXT_PUBLIC_BACKEND_URL` to the backend's base URL (e.g. https://my-backend.example.com).

Commands to run locally:

```bash
cd web
npm install
npm run dev
```

Then build for production:

```bash
npm run build
npm start
```

On Vercel, set `NEXT_PUBLIC_BACKEND_URL` in Project Settings → Environment Variables.
