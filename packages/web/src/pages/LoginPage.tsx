import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

export function LoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => navigate("/dashboard"), 600);
  }

  return (
    <div className="min-h-screen bg-bg-root grid-bg flex items-center justify-center relative">
      <div className="ambient-glow" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-[400px] mx-4"
      >
        <div className="bg-bg-surface border border-border rounded-xl p-8">
          {/* Brand */}
          <div className="text-center mb-8">
            <h1 className="font-serif text-3xl tracking-tight">
              Fin<span className="text-accent">Flow</span>
            </h1>
            <p className="text-text-secondary text-sm mt-2">
              Quality-Assured Financial Content
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                type="email"
                defaultValue="alex@wordwidefx.com"
                className="w-full bg-bg-app border border-border-light rounded-md px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/20 transition-all"
              />
            </div>

            <div>
              <label className="block text-[11px] font-medium text-text-secondary uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                defaultValue="demo123"
                className="w-full bg-bg-app border border-border-light rounded-md px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/40 focus:ring-1 focus:ring-accent/20 transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-accent hover:bg-accent/90 text-text-inverse font-medium py-2.5 rounded-md transition-all hover:-translate-y-px disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="text-center text-text-muted text-xs mt-6">
            Prototype Demo — OANDA Profile
          </p>
        </div>

        <p className="text-center text-text-muted text-[11px] mt-4">
          WordwideFX &middot; Since 2011 &middot; Barcelona
        </p>
      </motion.div>
    </div>
  );
}
