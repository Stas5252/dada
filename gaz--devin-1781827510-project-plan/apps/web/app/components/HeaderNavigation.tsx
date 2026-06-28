"use client";

import { useState } from "react";
import Link from "next/link";
import { Menu, X } from "lucide-react";

export function HeaderNavigation() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/10 bg-black">
      <div className="container mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 bg-white text-black flex items-center justify-center font-bold text-[10px] tracking-tighter">
            CF
          </div>
          <span className="font-semibold text-base tracking-tight text-white">
            CallForce
          </span>
        </div>
        
        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-zinc-400">
          <a href="#features" className="hover:text-white transition-colors">Платформа</a>
          <a href="#byok" className="hover:text-white transition-colors">BYOK</a>
          <a href="#compare" className="hover:text-white transition-colors">Сравнение</a>
          <a href="#pricing" className="hover:text-white transition-colors">Тарифы</a>
        </nav>
        
        <div className="hidden md:flex items-center gap-4">
          <Link href="/login" className="text-sm font-medium text-zinc-300 hover:text-white transition-colors">
            Войти
          </Link>
          <Link href="/dashboard" className="text-sm font-medium bg-white text-black px-4 py-2 rounded hover:bg-zinc-200 transition-colors">
            Панель управления
          </Link>
        </div>

        {/* Mobile Toggle */}
        <button 
          className="md:hidden text-zinc-400 hover:text-white"
          onClick={() => setIsOpen(!isOpen)}
        >
          {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="md:hidden border-t border-white/10 bg-black absolute w-full left-0 p-6 flex flex-col gap-6 shadow-2xl">
          <nav className="flex flex-col gap-4 text-sm font-medium text-zinc-400">
            <a href="#features" onClick={() => setIsOpen(false)} className="hover:text-white">Платформа</a>
            <a href="#byok" onClick={() => setIsOpen(false)} className="hover:text-white">BYOK</a>
            <a href="#compare" onClick={() => setIsOpen(false)} className="hover:text-white">Сравнение</a>
            <a href="#pricing" onClick={() => setIsOpen(false)} className="hover:text-white">Тарифы</a>
          </nav>
          <div className="flex flex-col gap-4 pt-4 border-t border-white/10">
            <Link href="/login" onClick={() => setIsOpen(false)} className="text-sm font-medium text-white text-center border border-white/20 py-2.5 rounded">
              Войти
            </Link>
            <Link href="/dashboard" onClick={() => setIsOpen(false)} className="text-sm font-medium bg-white text-black text-center py-2.5 rounded">
              Панель управления
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
