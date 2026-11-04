"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Bird,
  BookOpen,
  Camera,
  Clock3,
  Home,
  LogOut,
  Mail,
  Search,
} from "lucide-react";
import { isSignedIn, signOut } from "@/lib/auth";

const navItems = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/identify", label: "Identify Bird", icon: Search },
  { href: "/guide", label: "Bird Guide", icon: BookOpen },
  { href: "/history", label: "History", icon: Clock3 },
  { href: "/contact", label: "Contact", icon: Mail },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState(pathname === "/signin");

  useEffect(() => {
    if (pathname === "/signin") {
      setAuthorized(true);
      return;
    }

    if (!isSignedIn()) {
      router.replace("/signin");
      return;
    }

    setAuthorized(true);
  }, [pathname, router]);

  function handleLogout() {
    signOut();
    router.replace("/signin");
  }

  if (pathname === "/signin") {
    return children;
  }

  if (!authorized) {
    return <main className="auth-loading">Checking access...</main>;
  }

  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="sidebar-brand" href="/">
          <Bird size={38} />
          <span>
            <strong>AI Bird</strong>
            <small>Species Detection</small>
          </span>
        </Link>

        <nav className="side-nav" aria-label="Dashboard navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
            return (
              <Link key={item.href} className={isActive ? "active" : ""} href={item.href}>
                <Icon size={19} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <button className="logout-button" onClick={handleLogout} type="button">
          <LogOut size={18} />
          Logout
        </button>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div className="search-box">
            <Search size={17} />
            <span>Bird identification demo</span>
          </div>
          <div className="topbar-actions">
            <span className="notification-dot" />
            <span className="avatar">FA</span>
            <strong>Farhan Ahmad</strong>
          </div>
        </header>
        {children}
      </div>
    </div>
  );
}
