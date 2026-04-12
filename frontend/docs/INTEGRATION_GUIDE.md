# 📘 VOCHE: The Complete Onboarding & Integration Manual


This guide is designed specifically for you. By the end of this page, you will know exactly how Voche works.

---

## 🧠 1. What is an API? (The Basics)

Imagine you are at a restaurant:
1.  **The Frontend (Client)**: You (the hungry customer). You look at the menu (UI) and decide what you want.
2.  **The Backend (Server)**: The Kitchen. They have all the ingredients (Database) and know how to cook the food (Logic).
3.  **The API (Waiter)**: The messenger. You tell the waiter what you want (**Request**), the waiter goes to the kitchen, and then brings the food back to you (**Response**).

### Key Terms:
-   **Request**: Sending information to the backend (e.g., "Here is my email and password, let me in!").
-   **Response**: The data the backend sends back (e.g., "Okay, here is your user profile!").
-   **JSON**: The "language" they use to talk. It looks like a simple list:
    ```json
    { "name": "Shivani", "role": "Frontend Dev" }
    ```

---

## 🔐 2. Understanding Authentication (The ID Card)

When you log in, the backend gives you an **Access Token**.

-   **Analogy**: Think of it as a **Digital ID Card**.
-   **Why we need it**: The backend is "forgetful." Every time you ask for data, it doesn't remember who you are. You must show your ID card (Token) with *every single request*.
-   **Where is it stored?**: We keep it in **Cookies**. Think of Cookies as a secure vault in your browser that the backend can see.
-   **How it's sent**: Our "Smart Messenger" (`apiClient.ts`) automatically grabs this ID card from the vault and attaches it to your requests so you don't have to!

---

## 🔌 3. Postman: Testing Before Coding

Before writing any React code, we use a tool called **Postman** to make sure the "Kitchen" (Backend) is working.

### EXACT STEPS to Test Login:
1.  **Open Postman**.
2.  **Go to "Workspaces"** -> Select **VOCHE**.
3.  **Find the Folder**: You will see folders like `[Admin]`, `[HCP]`, and `Authentication`.
4.  **🚨 CRITICAL RULE**: For now, **IGNORE** any folder that has `[Admin]` or `[HCP]` in the name. Those are for other roles. Only use the ones with no prefix or `Authentication`.
5.  **Click "Login"**: Inside the Authentication folder.
6.  **Click "Send"**: (The big blue button).

### 🧪 Understanding the Response
When you click send, you will see a result like this:
```json
{
  "access_token": "eyJhbG...",
  "token_type": "bearer"...
}
```
-   **access_token**: This is your "ID Card."
-   **token_type**: "Bearer" just means "The person holding this token has the power."
-   **Frontend Use**: Our code takes this `access_token` and saves it in your browser's Cookies immediately.

---

## 🛠️ 4. Local Setup 

You need the Voche backend running on your computer to test your frontend.

### Step 1: Install Tools
-   **Docker**: Think of this as a "Home for Services." It runs our Database (PostgreSQL) and Cache (Redis) in little containers so they don't mess up your computer.

### Step 2: Environment (.env)
Create a file named `.env` in the `backend/` folder. Use this config:
```bash
PROJECT_NAME="VOCE App"
DATABASE_URL="postgresql://postgres:yacine@localhost:5432/voce"
REDIS_URL="redis://localhost:6379"
SECRET_KEY="your_secret_key"
CORS_ORIGINS='["http://localhost:5173"]' # Tells backend it's safe to talk to our React app
```

### Step 3: Run Docker
In your terminal, run:
```bash
docker-compose up -d --build
```
-   Check Docker Desktop: All lights should be **GREEN**.
-   **Health Check**: Visit [http://localhost:8000/api/v1/system/health](http://localhost:8000/api/v1/system/health). If you see `"status": "ok"`, you are ready!

---

## ⚛️ 5. Inside the Frontend 

We use 5 main parts to handle data. Here is what they actually do:

### 1. 🗺️ `lib/api.ts` (The Map)
This file lists every "address" in the backend. 
- **Rule**: Never type `/api/v1/something` in a component. Always add it to this map first.

### 2. 🌐 `lib/apiClient.ts` (The Smart Messenger)
This is a "Smart Messenger" built with **Axios**.
- **Request Guard**: Every time we send a message, it automatically stops by the Cookie Vault, grabs your "ID Card" (Token), and attaches it.
- **Response Guard**: If the backend says "I don't know you/Your ID expired" (Error 401), this messenger automatically kicks you back to the login page for safety.

### 3. 🧠 `lib/reactQuery.ts`
Instead of you manually fetching and setting states, **React Query** manages everything:
-   **Loading**: It tells you if the data is still being "cooked."
-   **Error**: It tells you if the kitchen burned the food.
-   **Caching**: If you go back to a page, it remembers the data so the user doesn't have to wait again.

### 4. 🔐 `hooks/useAuth.ts`
**This is the ONLY thing you will ever use for login/register.**
-   It provides `user`, `isAuthenticated`, `login()`, and `logout()`.
-   **Why?**: So you don't have to write complex logic in your Page components.

### 5. 🏢 Contexts: Global Storage
| Context | Purpose | Example |
| :--- | :--- | :--- |
| **AuthContext** | Global Login State | "Is Shivani logged in?" |
| **DataContext** | Local App Storage | "What trials did Shivani save to her list?" |

---

## 🔁 6. The Login Flow: Step-by-Step

What happens when you click the "Login" button?
1.  **User types**: Email and Password.
2.  **`useAuth().login()`**: The frontend calls the login brain.
3.  **`authService.login()`**: The "Employee" prepares the request.
4.  **`apiClient.post()`**: The "Messenger" sends it (adding headers automatically).
5.  **Backend Returns Token**: Kitchen sends back the "ID Card."
6.  **Saved in Cookies**: The "Messenger" puts the ID in the vault.
7.  **React Query Refreshes**: It asks for your profile info using the new ID.
8.  **Redirect**: You are teleported to the Dashboard!

---

## 🔄 7. How to Add a New Feature (Example: "Get Trials")

Let's say you want to show a list of Clinical Trials:

1.  **Test in Postman**: Make sure `GET /api/v1/clinical/trials` works and returns a list.
2.  **Add to `api.ts`**:
    ```typescript
    export const CLINICAL = { TRIALS: `${API_BASE}/clinical/trials` };
    ```
3.  **Create Service (`trialService.ts`)**:
    ```typescript
    export const getTrials = async () => {
      const response = await apiClient.get(CLINICAL.TRIALS);
      return response.data;
    };
    ```
4.  **Use in Component**:
    ```tsx
    const { data: trials, isLoading } = useQuery({ 
      queryKey: ['trials'], 
      queryFn: getTrials 
    });

    if (isLoading) return <Spinner />;
    return trials.map(t => <TrialCard trial={t} />);
    ```

---

## ⚠️ 8. Common Errors & How to Fix Them

-   **"CORS Error"**: The backend is blocking the frontend. **Fix**: Check `CORS_ORIGINS` in your backend `.env`. It must match your frontend URL (usually `http://localhost:5173`).
-   **"401 Unauthorized"**: Your ID card (Token) is missing or expired. **Fix**: Log out and log back in.
-   **"Network Error / ECONNREFUSED"**: The backend isn't running. **Fix**: Go to Docker and make sure `voce-backend` is green.
-   **"Token Missing"**: The `apiClient` didn't find the cookie. **Fix**: Check your browser inspector -> Application -> Cookies. If `voche_token` isn't there, login failed.

---

## 🌐 9. Why We Made These Decisions (Audit)

1.  **Why Cookies?**: Because they are "HttpOnly" compatible, meaning hackers can't steal them as easily as `localStorage`.
2.  **Why Interceptors?**: We don't want you to manually add `Authorization: Bearer ...` 100 times. Automation saves time and prevents bugs.
3.  **Why React Query?**: It keeps the app fast. If you click a trial, go back, and click it again, it shows up instantly because of the "Cache."
4.  **Why Central API Map?**: Because if we ever rename `/api/v1/auth/login` to `/api/v2/secure-login`, we only change **one line** in `api.ts` instead of searching through 50 files.
