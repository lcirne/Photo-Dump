import React, { useMemo, useState } from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, ImagePlus, LogOut, Plus, RefreshCcw, UploadCloud } from "lucide-react";
import "./styles.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type User = {
  id: number;
  username: string;
  email: string;
};

type Album = {
  id: number;
  title: string;
  description: string;
  visibility: "private" | "unlisted" | "public";
  photo_count: number;
};

type Photo = {
  id: number;
  album: number | null;
  album_title: string | null;
  original_filename: string;
  width: number | null;
  height: number | null;
  upload_status: "processing" | "ready" | "failed";
  created_at: string;
  original_url: string;
  thumbnail_url: string | null;
  preview_url: string | null;
};

type Dashboard = {
  albums: Album[];
  recent_photos: Photo[];
  stats: {
    album_count: number;
    photo_count: number;
    processing_count: number;
  };
};

type AuthState = {
  token: string;
  user: User;
};

const queryClient = new QueryClient();

function getStoredAuth(): AuthState | null {
  const raw = localStorage.getItem("photo_dump_auth");
  return raw ? JSON.parse(raw) : null;
}

async function apiRequest<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...options.headers
    }
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed." }));
    throw new Error(JSON.stringify(error));
  }

  return response.json();
}

function App() {
  const [auth, setAuth] = useState<AuthState | null>(getStoredAuth());

  function saveAuth(next: AuthState | null) {
    setAuth(next);
    if (next) {
      localStorage.setItem("photo_dump_auth", JSON.stringify(next));
    } else {
      localStorage.removeItem("photo_dump_auth");
      queryClient.clear();
    }
  }

  return (
    <QueryClientProvider client={queryClient}>
      {auth ? <DashboardPage auth={auth} onLogout={() => saveAuth(null)} /> : <AuthPage onAuth={saveAuth} />}
    </QueryClientProvider>
  );
}

function AuthPage({ onAuth }: { onAuth: (auth: AuthState) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const mutation = useMutation({
    mutationFn: () =>
      apiRequest<AuthState>(mode === "login" ? "/auth/login" : "/auth/register", {
        method: "POST",
        body: JSON.stringify(mode === "login" ? { username, password } : { username, email, password })
      }),
    onSuccess: onAuth
  });

  return (
    <main className="auth-shell">
      <section className="auth-panel">
        <div>
          <p className="eyebrow">Photo-Dump</p>
          <h1>Camera uploads, organized fast.</h1>
        </div>
        <div className="segmented">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Register</button>
        </div>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
        >
          <label>
            Username
            <input value={username} onChange={(event) => setUsername(event.target.value)} required />
          </label>
          {mode === "register" ? (
            <label>
              Email
              <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
          ) : null}
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} />
          </label>
          <button className="primary" disabled={mutation.isPending}>
            {mode === "login" ? "Login" : "Create Account"}
          </button>
          {mutation.error ? <p className="error">{mutation.error.message}</p> : null}
        </form>
      </section>
    </main>
  );
}

function DashboardPage({ auth, onLogout }: { auth: AuthState; onLogout: () => void }) {
  const [selectedAlbum, setSelectedAlbum] = useState<number | "all">("all");
  const token = auth.token;
  const queryClient = useQueryClient();
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiRequest<Dashboard>("/dashboard", {}, token),
    refetchInterval: 5000
  });
  const photos = useQuery({
    queryKey: ["photos", selectedAlbum],
    queryFn: () => apiRequest<Photo[]>(`/photos${selectedAlbum === "all" ? "" : `?album=${selectedAlbum}`}`, {}, token),
    refetchInterval: 5000
  });
  const albums = dashboard.data?.albums ?? [];

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Photo-Dump</p>
          <h1>{auth.user.username}'s library</h1>
        </div>
        <div className="toolbar">
          <button className="icon-button" title="Refresh" onClick={() => queryClient.invalidateQueries()}>
            <RefreshCcw size={18} />
          </button>
          <button className="icon-button" title="Logout" onClick={onLogout}>
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <section className="stats-row">
        <Metric label="Photos" value={dashboard.data?.stats.photo_count ?? 0} />
        <Metric label="Albums" value={dashboard.data?.stats.album_count ?? 0} />
        <Metric label="Processing" value={dashboard.data?.stats.processing_count ?? 0} />
      </section>

      <section className="workspace">
        <aside>
          <AlbumCreator token={token} />
          <div className="album-list">
            <button className={selectedAlbum === "all" ? "selected" : ""} onClick={() => setSelectedAlbum("all")}>
              All photos
            </button>
            {albums.map((album) => (
              <button className={selectedAlbum === album.id ? "selected" : ""} key={album.id} onClick={() => setSelectedAlbum(album.id)}>
                <span>{album.title}</span>
                <small>{album.photo_count}</small>
              </button>
            ))}
          </div>
        </aside>
        <section className="gallery-panel">
          <UploadPanel token={token} albums={albums} selectedAlbum={selectedAlbum} />
          {dashboard.isLoading || photos.isLoading ? <p className="muted">Loading library...</p> : null}
          <div className="photo-grid">
            {(photos.data ?? []).map((photo) => (
              <PhotoCard key={photo.id} photo={photo} />
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AlbumCreator({ token }: { token: string }) {
  const [title, setTitle] = useState("");
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      apiRequest<Album>("/albums", {
        method: "POST",
        body: JSON.stringify({ title, visibility: "private" })
      }, token),
    onSuccess: () => {
      setTitle("");
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    }
  });

  return (
    <form className="album-creator" onSubmit={(event) => {
      event.preventDefault();
      mutation.mutate();
    }}>
      <input placeholder="New album" value={title} onChange={(event) => setTitle(event.target.value)} required />
      <button title="Create album" disabled={mutation.isPending}>
        <Plus size={18} />
      </button>
    </form>
  );
}

function UploadPanel({ token, albums, selectedAlbum }: { token: string; albums: Album[]; selectedAlbum: number | "all" }) {
  const [album, setAlbum] = useState(String(selectedAlbum === "all" ? "" : selectedAlbum));
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: (file: File) => {
      const body = new FormData();
      body.append("file", file);
      if (album) {
        body.append("album", album);
      }
      return apiRequest<Photo>("/photos/upload", { method: "POST", body }, token);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["photos"] });
    }
  });

  const statusText = useMemo(() => {
    if (mutation.isPending) return "Uploading...";
    if (mutation.isSuccess) return "Upload queued";
    if (mutation.isError) return mutation.error.message;
    return "";
  }, [mutation.error, mutation.isError, mutation.isPending, mutation.isSuccess]);

  return (
    <div className="upload-panel">
      <div>
        <ImagePlus size={22} />
        <strong>Upload image</strong>
      </div>
      <select value={album} onChange={(event) => setAlbum(event.target.value)}>
        <option value="">No album</option>
        {albums.map((item) => (
          <option key={item.id} value={item.id}>{item.title}</option>
        ))}
      </select>
      <label className="upload-button">
        <UploadCloud size={18} />
        <span>Choose File</span>
        <input
          type="file"
          accept="image/*"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) mutation.mutate(file);
          }}
        />
      </label>
      {statusText ? <small className={mutation.isError ? "error" : "muted"}>{statusText}</small> : null}
    </div>
  );
}

function PhotoCard({ photo }: { photo: Photo }) {
  return (
    <article className="photo-card">
      <div className="thumb">
        {photo.thumbnail_url || photo.preview_url ? (
          <img src={photo.thumbnail_url ?? photo.preview_url ?? ""} alt={photo.original_filename} />
        ) : (
          <span>{photo.upload_status}</span>
        )}
      </div>
      <div className="photo-meta">
        <div>
          <strong>{photo.original_filename}</strong>
          <small>{photo.album_title ?? "No album"} · {photo.width && photo.height ? `${photo.width}x${photo.height}` : photo.upload_status}</small>
        </div>
        <a href={photo.original_url} title="Download original" target="_blank" rel="noreferrer">
          <Download size={18} />
        </a>
      </div>
    </article>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
