# VOCE MVP – API Headnotes

### 🔐 1. Authentication & Users

* **Register**
  * `POST /auth/register`
    * `{ email, password, role_type }`


* **Login**
  * `POST /auth/token`
    * `{ username, password }`
    * *Returns: JWT Access Token*


* **Get My Profile**
  * `GET /users/me`
    * *Headers: Authorization: Bearer <token>*


* **Update Profile (Patients)**
  * `PUT /users/me/profile`
    * `{ disease_interests: ["HIV", "TB"], location: "Kenya", language: "fr" }`


* **Request Verification (HCPs)**
  * `POST /users/verification`
    * `{ file: <medical_license.pdf> }`



---

### 🔎 2. Clinical Trial Navigator (The Engine)

* **Search Trials**
  * `GET /trials`
    * `?disease=Malaria&country=South_Africa&status=Recruiting`


* **Get One Trial**
  * `GET /trials/{id}`
    * *Response: { title, summary, hospitals_list }*


* **Save Bookmark**
  * `POST /trials/{id}/save`
    * *Requires: Auth (Patient)*


* **"Connect" (Express Interest)**
  * `POST /trials/{id}/connect`
    * `{ consent_agreed: true }`
    * *Action: Adds user to 'trial_leads' table. No external email sent yet.*


* **Download Protocol (HCP Only)**
  * `GET /trials/{id}/protocol`
    * *Requires: Auth (Verified HCP)*



---

### 📚 3. Education & Chat

* **List Resources**
  * `GET /resources`
    * `?tag=Advocacy&type=Video`


* **Get Resource Details**
  * `GET /resources/{id}`


* **Chat Triage (Bot)**
  * `POST /chat/triage`
    * `{ message: "What is informed consent?" }`
    * *Returns: { text: "Here is a guide...", link: "/resources/12" }*



---

### 💬 4. Community Forums

* **List Topics**
  * `GET /forums/topics`


* **List Posts in Topic**
  * `GET /forums/{topic_id}/posts`


* **CUD Post**
  * `POST /forums/{topic_id}/posts`
    * `{ content: "Has anyone tried this clinic?" }`
  * `PUT /forums/{topic_id}/posts/{id}`
    * `{ content: "Has anyone tried this clinic?" }`
  * `DELETE /forums/{topic_id}/posts/{id}`


* **Report Post**
  * `POST /forums/posts/{id}/report`
  * `{ reason: "Misinformation" }`



---

### 🛡️ 5. Admin (Internal)

* **Upload Trials (CSV)**
  * `POST /admin/trials/upload`
    * `{ file: <trials_data.csv> }`


* **Verify HCP User**
  * `PUT /admin/users/{id}/verify`
    * `{ status: "VERIFIED" }`


* **Approve Resource**
  * `PUT /admin/resources/{id}/publish`


* **Platform Stats**
  * `GET /admin/analytics`
    * *Returns: { total_users, top_searched_disease }*