# 📘 VOCE — Beginner Onboarding Guide (Shivani Version)

This guide will help you understand **everything from zero**.

---

# 1. What is an API?

Imagine this:

* You → Frontend (React)
* Kitchen → Backend (Server)
* Waiter → API

### Flow:

1. You ask for food → (Request)
2. Waiter goes to kitchen
3. Kitchen prepares food
4. Waiter brings it back → (Response)

---

## 💬 Real Example (Login)

You send:

```json
{ "email": "test@mail.com", "password": "123456" }
```

Backend responds:

```json
{
  "access_token": "abc123..."
}
```

---

# 🔐 2. What is an Access Token?

After login, backend gives you:

👉 **access_token**

### Think of it like:

> Your **ID card**

---

## Why do we need it?

Because backend does NOT remember you.

So every time you request something:

👉 You must show your ID card

---

## Where do we store it?

👉 In **Cookies**

Think of cookies as:

> A small secure storage in your browser

---

## Do YOU send it manually?

❌ NO

👉 Our system does it automatically (you don’t worry about it)

---

# 🛠️ 3. FIRST — Run the Project

Before coding anything, you MUST run backend.

---

## Step 1 — Install Tools

You need:

* Docker → runs backend services
* Node.js → runs frontend

---

## Step 2 — Setup Backend `.env`

Go to:

```
backend/.env
```

Put this:

```bash
PROJECT_NAME="VOCE App"
DATABASE_URL="postgresql://postgres:yacine@localhost:5432/voce"
REDIS_URL="redis://localhost:6379"
SECRET_KEY="your_secret_key"
CORS_ORIGINS='["http://localhost:5173"]'
```

---

## Step 3 — Start Backend

Run:

```bash
docker-compose up -d --build
```

---

## Step 4 — Check Everything Works

Open browser:

👉 [http://localhost:8000/api/v1/system/health](http://localhost:8000/api/v1/system/health)

You should see:

```json
{ "status": "ok" }
```

---

## If NOT working:

* Check Docker → all containers GREEN
* Restart docker

---

# 🔌 5. Postman (TEST BEFORE CODE)

Before writing code, we test APIs.

---

## Step-by-step:

1. Open Postman
2. Go to **Workspaces**
3. Select **VOCHE**
4. Open folder **Authentication**

---

## 🚨 IMPORTANT RULE

Only use:

✅ endpoints WITHOUT `[Admin]`
✅ endpoints WITHOUT `[HCP]`

---

### Example:

✔ Use:

* login
* register

❌ DO NOT USE:

* [Admin] delete user
* [HCP] something

---

## 🧪 Test Login

Click:

👉 login → Send

---

## Response:

```json
{
  "access_token": "abc..."
}
```

---

## What happens here?

* Backend gives token
* This = your ID card

---

# 5. Frontend — How Everything Works

Now the important part.

---

## 🗺️ 1. `api.ts` → API List

This file contains all endpoints.

Example:

```ts
LOGIN: '/api/v1/auth/login'
```

---

### Why?

👉 So we don’t repeat URLs everywhere

---

## 🌐 2. `apiClient.ts` → The Smart Messenger

This file sends ALL requests.

---

### What it does:

1. Sends request
2. Adds token automatically
3. Handles errors

---

### Example:

Instead of:

❌ writing token manually

It does:

✔ automatically add:

```
Authorization: Bearer <token>
```

---

## 3. React Query → Data Manager

This is VERY IMPORTANT.

---

Instead of doing:

* useEffect
* useState
* manual fetch

👉 React Query does everything

---

### It handles:

* loading → isLoading
* error → error
* data → data
* caching → remembers data

---

## 🔐 4. `authService.ts`

This file talks to backend.

Example:

```ts
login(data)
register(data)
getMe()
```

---

👉 It does ONLY API calls
👉 No UI logic here

---

## 🧠 5. `useAuth.ts` (VERY IMPORTANT)

👉 This is what YOU will use

---

Instead of calling API:

You do:

```ts
const { login } = useAuth();
```

---

## 🏢 6. AuthContext

👉 Makes login available everywhere

---

## 📦 7. DataContext

👉 Stores app data (UI only)

---

### Difference:

| React Query | DataContext |
| ----------- | ----------- |
| Server data | UI data     |

---

# 6. LOGIN FLOW (STEP BY STEP)

When user clicks login:

---

1. User types email/password
2. Button clicked
3. `handleLogin()` runs
4. Calls `login()` from `useAuth`
5. Calls `authService.login()`
6. Calls API using `apiClient`
7. Backend returns token
8. Token saved in cookies
9. React Query fetches user
10. Redirect to dashboard

---

# 7. How YOU Add New Feature

Example: Get Trials

---

## Step 1 — Postman

Test:

```
GET /clinical/trials
```

---

## Step 2 — Add to `api.ts`

```ts
TRIALS: '/api/v1/clinical/trials'
```

---

## Step 3 — Create Service

```ts
export const getTrials = async () => {
  return (await apiClient.get(TRIALS)).data;
};
```

With errors handling (try & catch).

---

## Step 4 — Use in Component

```tsx
const { data, isLoading } = useQuery({
  queryKey: ['trials'],
  queryFn: getTrials
});
```

---

## Step 5 — Show Data

```tsx
data.map(trial => <div>{trial.title}</div>)
```

---

# ⚠️ 9. Common Errors (YOU WILL SEE THESE)


Shivani, as you start working, you will definitely see errors like this:

---

## ❌ Backend not running

Fix:
👉 run docker

---

## ❌ CORS error

Fix:
👉 check `CORS_ORIGINS`

---

## ❌ 401 error

Fix:
👉 login again

---

## ❌ No token

Fix:
👉 check cookies in browser


---


## ❌ Error

```ts
Cannot find name 'ForumPost'
```

👉 Fix:

* Import it from:

```ts
import type { ForumPost } from '../../types/db';
```

* Or add it in `types/db.ts` (based on backend schema)

---

## ❌ Error

```ts
Cannot find name 'mockForumPosts'
```

👉 Cause:

* Mock data was removed ❌

👉 Fix:

* Replace with real API:

```ts
const { data } = useQuery({
  queryKey: ['posts'],
  queryFn: getPosts
});
```

---

## Rule

❌ No mock data anymore
✅ Always use API + React Query

---

## 🧠 Think like this

Before:

> use mock data

Now:

> call API → service → useQuery


