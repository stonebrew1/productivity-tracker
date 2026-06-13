import { CheckCircle2, LoaderCircle, MailWarning, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "../api/client";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Confirming your email...");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState("error");
      setMessage("The verification link is incomplete.");
      return;
    }
    api.verifyEmail(token)
      .then((result) => {
        setState("success");
        setMessage(result.message);
      })
      .catch((error) => {
        setState("error");
        setMessage(error instanceof Error ? error.message : "Unable to confirm email.");
      });
  }, [searchParams]);

  return (
    <main className="verification-screen">
      <div className="brand"><span className="brand-mark"><Zap size={19} fill="currentColor" /></span><strong>Momentum</strong></div>
      <section>
        <span className={`verification-state ${state}`}>
          {state === "loading" ? <LoaderCircle size={28} /> : state === "success" ? <CheckCircle2 size={28} /> : <MailWarning size={28} />}
        </span>
        <h1>{state === "loading" ? "Confirming email" : state === "success" ? "Email confirmed" : "Link unavailable"}</h1>
        <p>{message}</p>
        {state !== "loading" && <Link to="/login">{state === "success" ? "Continue to sign in" : "Return to registration"}</Link>}
      </section>
    </main>
  );
}
