"use client";

import Link from "next/link";
import { messages } from "@/lib/i18n";
import {useSession} from "@/components/session";

export default function Home() {
  const {locale}=useSession();
  const t = messages(locale);
  return (
    <main>
      <section className="hero">
        <p className="eyebrow">{t.eyebrow}</p>
        <h1>{t.hero}</h1>
        <p className="lede">{t.sub}</p>
        <div className="actions">
          <Link className="button primary" href="/bookings/new">{t.book}<span aria-hidden>→</span></Link>
          <Link className="button quiet" href="/bookings">{t.track}</Link>
        </div>
        <div className="status-card" aria-label="Example pickup status">
          <div><small>{t.window}</small><strong>1:00–5:00 PM</strong></div>
          <div className="pulse" aria-hidden />
          <div><small>{t.estimate}</small><strong>About 18 min</strong></div>
          <p>{t.promise}</p>
        </div>
      </section>
      <section className="steps" aria-label="How Returnet works">
        {[["01", t.prep, t.prepBody], ["02", t.route, t.routeBody], ["03", t.proof, t.proofBody]].map(([n, title, body]) => (
          <article key={n}><span>{n}</span><h2>{title}</h2><p>{body}</p></article>
        ))}
      </section>
      <footer>{t.footer}</footer>
    </main>
  );
}
