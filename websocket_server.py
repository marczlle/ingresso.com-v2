from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
import json
import grpc
import time
import asyncio
import logging
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
import os

from seat_state_service import SeatStateService
from email_service import EmailService

load_dotenv()

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Seleção de Assentos • Cinemas Costa Dourada</title>
    <style>
        :root {
            --bg:#040b18;
            --panel:#0b1426;
            --panel-dark:#101b30;
            --panel-light:#1a2745;
            --accent:#6c7dff;
            --accent-strong:#4e5cff;
            --highlight:#f7c843;
            --blocked:#4c5674;
            --reserved:#1f2435;
            --text-soft:#8f9dc7;
            --text-muted:#65719a;
            --danger:#ff6b6b;
            --success:#5fe1a1;
        }
        *{box-sizing:border-box;margin:0;padding:0;}
        body{
            font-family:"Inter","Segoe UI",system-ui,-apple-system,sans-serif;
            background:var(--bg);
            color:#fff;
            min-height:100vh;
            display:flex;
            justify-content:center;
            padding:32px 24px 60px;
        }
        .app-shell{
            width:min(1200px,100%);
            display:flex;
            flex-direction:column;
            gap:18px;
        }
        .top-bar{
            background:#1c2f74;
            border-radius:18px;
            padding:18px 28px;
            display:flex;
            justify-content:space-between;
            align-items:center;
            box-shadow:0 12px 30px rgba(17,24,39,.4);
        }
        .top-bar .info-group{
            display:flex;
            gap:24px;
            font-weight:600;
        }
        .top-bar .info-badge{
            display:flex;
            align-items:center;
            gap:8px;
            font-size:0.95rem;
            letter-spacing:.02em;
        }
        .top-bar .info-badge svg{
            width:18px;
            height:18px;
        }
        .user-pill{
            background:rgba(255,255,255,.1);
            padding:8px 14px;
            border-radius:999px;
            font-size:0.9rem;
        }
        .seat-panel{
            background:var(--panel);
            border-radius:22px;
            padding:28px 32px 36px;
            box-shadow:0 40px 60px rgba(0,0,0,.45);
            display:flex;
            flex-direction:column;
            gap:24px;
        }
        .panel-header{
            display:flex;
            justify-content:space-between;
            align-items:center;
        }
        .panel-title{
            font-size:1.3rem;
            font-weight:600;
        }
        .text-small{
            font-size:0.9rem;
        }
        .seat-layout{
            display:grid;
            grid-template-columns:auto 1fr auto 60px;
            gap:16px;
            align-items:center;
        }
        .row-indicators{
            display:flex;
            flex-direction:column;
            gap:18px;
            font-weight:600;
            color:var(--text-soft);
        }
        .row-indicators span{
            text-align:center;
            opacity:0.6;
        }
        .seat-grid{
            background:var(--panel-dark);
            border-radius:26px;
            padding:28px 36px 36px;
            display:flex;
            flex-direction:column;
            gap:18px;
            position:relative;
            transition:transform .2s ease;
            transform-origin:center;
        }
        .seat-row{
            display:flex;
            align-items:center;
            gap:22px;
        }
        .seat-group{
            display:grid;
            grid-template-columns:repeat(14,32px);
            gap:12px;
        }
        .seat-group.right{
            grid-template-columns:repeat(6,32px);
        }
        .walkway{
            width:70px;
            height:90%;
            border-radius:18px;
            border:1px dashed rgba(255,255,255,.08);
            background:rgba(255,255,255,.02);
        }
        .seat{
            width:32px;
            height:32px;
            border-radius:50%;
            border:0;
            outline:none;
            background:#6a7bff;
            color:#0b1527;
            font-weight:600;
            cursor:pointer;
            display:flex;
            align-items:center;
            justify-content:center;
            position:relative;
            transition:transform .15s ease, background .2s ease, box-shadow .2s ease;
        }
        .seat::after{
            content:attr(data-label);
            font-size:0.56rem;
            color:#0b1524;
            font-weight:700;
            opacity:0;
            transition:opacity .2s ease;
        }
        .seat-grid.show-labels .seat::after{
            opacity:1;
        }
        .seat.available{background:#9fa9ff;}
        .seat.selected{
            background:var(--highlight);
            color:#1d1b0b;
            box-shadow:0 0 0 4px rgba(247,200,67,.25);
        }
        .seat.blocked{
            background:var(--blocked);
            color:#d7ddff;
            cursor:not-allowed;
            opacity:0.8;
        }
        .seat.reserved{
            background:#2f364d;
            color:#94a2d6;
            cursor:not-allowed;
            border:2px solid rgba(255,255,255,.1);
        }
        .seat.pending{
            animation:pulse 1s infinite;
            background:#ffd166;
        }
        @keyframes pulse{
            0%{box-shadow:0 0 0 0 rgba(255,209,102,.4);}
            70%{box-shadow:0 0 0 10px rgba(255,209,102,0);}
            100%{box-shadow:0 0 0 0 rgba(255,209,102,0);}
        }
        .seat.wheelchair{
            border:2px solid var(--accent);
            background:#0b1524;
            color:var(--accent);
        }
        .seat.wheelchair::before{
            content:"♿";
            position:absolute;
            font-size:0.9rem;
            color:var(--accent);
            opacity:0.85;
        }
        .seat:disabled{
            cursor:not-allowed;
        }
        .zoom-stack{
            background:var(--panel-light);
            border-radius:36px;
            padding:14px 10px;
            display:flex;
            flex-direction:column;
            align-items:center;
            gap:14px;
        }
        .zoom-stack button{
            width:30px;
            height:30px;
            border-radius:50%;
            border:none;
            background:var(--panel);
            color:#fff;
            font-size:1.1rem;
            cursor:pointer;
        }
        .zoom-stack input[type=range]{
            writing-mode:bt-lr;
            -webkit-appearance:none;
            width:140px;
            transform:rotate(-90deg);
        }
        .zoom-stack input[type=range]::-webkit-slider-thumb{
            -webkit-appearance:none;
            width:18px;
            height:18px;
            border-radius:50%;
            background:var(--accent);
            border:3px solid var(--panel);
            box-shadow:0 0 0 3px rgba(108,125,255,.2);
        }
        .zoom-stack input[type=range]::-webkit-slider-runnable-track{
            height:6px;
            background:rgba(255,255,255,.2);
            border-radius:6px;
        }
        .screen-label{
            margin-top:-8px;
            display:flex;
            justify-content:center;
            align-items:center;
            flex-direction:column;
            gap:8px;
        }
        .screen-bar{
            width:80%;
            height:10px;
            border-radius:40px;
            background:linear-gradient(90deg, rgba(255,255,255,.5), rgba(255,255,255,.1));
        }
        .toggle-row{
            display:flex;
            justify-content:center;
            align-items:center;
            gap:12px;
            color:var(--text-soft);
            font-size:0.9rem;
        }
        .toggle{
            width:46px;
            height:24px;
            border-radius:999px;
            position:relative;
            cursor:pointer;
            display:inline-flex;
            align-items:center;
        }
        .toggle input{
            opacity:0;
            width:0;
            height:0;
            position:absolute;
        }
        .toggle-slider{
            width:100%;
            height:100%;
            border-radius:999px;
            background:rgba(255,255,255,.15);
            position:relative;
            transition:background .2s ease;
        }
        .toggle-slider::after{
            content:"";
            width:18px;
            height:18px;
            border-radius:50%;
            background:#fff;
            position:absolute;
            top:3px;
            left:4px;
            transition:transform .2s ease;
        }
        .toggle input:checked + .toggle-slider{
            background:var(--accent);
        }
        .toggle input:checked + .toggle-slider::after{
            transform:translateX(20px);
        }
        .legend{
            display:flex;
            gap:18px;
            flex-wrap:wrap;
            color:var(--text-soft);
            font-size:0.9rem;
        }
        .legend-item{
            display:flex;
            align-items:center;
            gap:8px;
        }
        .legend-swatch{
            width:16px;
            height:16px;
            border-radius:50%;
        }
        .legend-swatch.available{background:#9fa9ff;}
        .legend-swatch.selected{background:var(--highlight);}
        .legend-swatch.blocked{background:var(--blocked);}
        .legend-swatch.reserved{background:#2f364d;}
        .legend-swatch.wheelchair{
            border:2px solid var(--accent);
            background:transparent;
        }
        .payment-section{
            background:var(--panel-light);
            border-radius:18px;
            padding:18px 22px;
            display:flex;
            justify-content:space-between;
            align-items:center;
            flex-wrap:wrap;
            gap:14px;
        }
        .primary-button{
            background:var(--accent-strong);
            color:#fff;
            border:none;
            border-radius:999px;
            padding:12px 26px;
            font-weight:600;
            font-size:0.95rem;
            cursor:pointer;
            transition:opacity .2s ease, transform .2s ease, box-shadow .2s ease;
            box-shadow:0 10px 25px rgba(78,92,255,.35);
        }
        .primary-button:disabled{
            opacity:0.4;
            cursor:not-allowed;
            box-shadow:none;
            transform:none;
        }
        .payment-hint{
            color:var(--text-soft);
            font-size:0.9rem;
        }
        .status-panel{
            background:var(--panel-dark);
            border-radius:18px;
            padding:18px 22px;
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:16px;
        }
        .status-text{
            font-weight:500;
        }
        .status-text[data-tone="error"]{color:var(--danger);}
        .status-text[data-tone="success"]{color:var(--success);}
        .activity-feed{
            list-style:none;
            color:var(--text-muted);
            font-size:0.85rem;
            display:flex;
            gap:12px;
        }
        .activity-feed li{
            background:rgba(255,255,255,.04);
            padding:8px 12px;
            border-radius:12px;
        }
        .modal{
            position:fixed;
            inset:0;
            background:rgba(3,8,17,.78);
            display:flex;
            justify-content:center;
            align-items:center;
            visibility:hidden;
            opacity:0;
            transition:opacity .2s ease, visibility .2s ease;
            padding:20px;
            z-index:20;
        }
        .modal.visible{
            visibility:visible;
            opacity:1;
        }
        .modal-card{
            background:var(--panel);
            border-radius:20px;
            width:min(460px,100%);
            padding:28px;
            box-shadow:0 30px 60px rgba(0,0,0,.5);
            display:flex;
            flex-direction:column;
            gap:18px;
            position:relative;
        }
        .modal-card h3{
            margin-bottom:6px;
        }
        .modal-close{
            position:absolute;
            top:18px;
            right:22px;
            background:transparent;
            border:none;
            color:#fff;
            font-size:1.5rem;
            cursor:pointer;
        }
        .form-grid{
            display:flex;
            flex-direction:column;
            gap:14px;
        }
        .form-grid label{
            font-size:0.85rem;
            color:var(--text-soft);
            display:flex;
            flex-direction:column;
            gap:6px;
        }
        .form-grid input{
            border-radius:12px;
            border:1px solid rgba(255,255,255,.15);
            background:var(--panel-dark);
            padding:12px;
            color:#fff;
            font-size:0.95rem;
        }
        .form-actions{
            display:flex;
            justify-content:flex-end;
            gap:12px;
        }
        .ghost-button{
            background:transparent;
            border:1px solid rgba(255,255,255,.25);
            color:#fff;
            border-radius:999px;
            padding:10px 20px;
            cursor:pointer;
        }
        @media (max-width:950px){
            .seat-layout{
                grid-template-columns:1fr;
            }
            .row-indicators,.zoom-stack{
                display:none;
            }
        }
    </style>
</head>
<body>
    <div class="app-shell">
        <header class="top-bar">
            <div class="info-group">
                <div class="info-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 2C8 2 4 5 4 10c0 5.25 7.5 12 8 12s8-6.75 8-12c0-5-4-8-8-8z"/><circle cx="12" cy="10" r="3"/></svg>
                    Cinemas Costa Dourada · SALA 1
                </div>
                <div class="info-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M8 7V3m8 4V3M3 11h18M5 21h14a2 2 0 0 0 2-2V7H3v12a2 2 0 0 0 2 2z"/></svg>
                    SÁB 13/12
                </div>
                <div class="info-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2"><path d="M12 6v6l4 2"/><circle cx="12" cy="12" r="10"/></svg>
                    17:45
                </div>
            </div>
            <div class="user-pill">Usuário · <span id="user-display">--</span></div>
        </header>

        <section class="seat-panel">
            <div class="panel-header">
                <p class="panel-title">Escolha suas poltronas</p>
                <p class="text-small" style="color:var(--text-soft);">Tempo de bloqueio: 5 min</p>
            </div>

            <div class="seat-layout">
                <div class="row-indicators" id="row-labels-left"></div>
                <div class="seat-grid" id="seat-grid"></div>
                <div class="row-indicators" id="row-labels-right"></div>
                <div class="zoom-stack">
                    <button type="button" id="zoom-in">+</button>
                    <input type="range" id="zoom-range" min="80" max="130" value="100" />
                    <button type="button" id="zoom-out">−</button>
                </div>
            </div>

            <div class="screen-label">
                <div class="screen-bar"></div>
                <span style="text-transform:uppercase; letter-spacing:.4em; color:var(--text-muted); font-size:0.8rem;">Tela</span>
            </div>

            <div class="toggle-row">
                Exibir números dos assentos
                <label class="toggle">
                    <input type="checkbox" id="toggle-seat-number" />
                    <span class="toggle-slider"></span>
                </label>
            </div>

            <div class="legend">
                <div class="legend-item"><span class="legend-swatch available"></span>Disponível</div>
                <div class="legend-item"><span class="legend-swatch selected"></span>Selecionado</div>
                <div class="legend-item"><span class="legend-swatch blocked"></span>Bloqueado</div>
                <div class="legend-item"><span class="legend-swatch reserved"></span>Ocupado</div>
                <div class="legend-item"><span class="legend-swatch wheelchair"></span>Cadeirante</div>
            </div>

            <div class="payment-section">
                <div>
                    <p style="font-weight:600;">Pagamento</p>
                    <p class="payment-hint" id="payment-hint">Selecione ao menos uma poltrona.</p>
                </div>
                <button id="confirm-btn" class="primary-button" type="button" disabled>Confirmar pagamento</button>
            </div>

            <div class="status-panel">
                <p id="status-text" class="status-text" data-tone="info">Conectando ao servidor...</p>
                <ul class="activity-feed" id="activity-feed"></ul>
            </div>
        </section>
    </div>

    <div class="modal" id="payment-modal">
        <div class="modal-card">
            <button class="modal-close" type="button" data-close-modal>&times;</button>
            <div>
                <h3>Confirmar pagamento</h3>
                <p class="payment-hint" id="seat-summary">Selecione ao menos uma poltrona.</p>
            </div>
            <form id="payment-form" class="form-grid">
                <label>
                    Nome completo
                    <input type="text" name="nomeCompleto" placeholder="Ex.: Maria Oliveira" required />
                </label>
                <label>
                    CPF
                    <input type="text" name="cpf" placeholder="000.000.000-00" required />
                </label>
                <label>
                    E-mail
                    <input type="email" name="email" placeholder="voce@email.com" required />
                </label>
                <div class="form-actions">
                    <button type="button" class="ghost-button" data-close-modal>Cancelar</button>
                    <button type="submit" class="primary-button" id="submit-payment-btn">Confirmar</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        const SESSION_ID = "S001";
        const WS_PROTOCOL = location.protocol === "https:" ? "wss" : "ws";
        const WS_URL = `${WS_PROTOCOL}://${location.host}/ws/reserva?sessao=${encodeURIComponent(SESSION_ID)}`;
        const ROWS = ["J","I","H","G","F","E","D","C","B","A"];
        const LEFT_SEATS = 14;
        const RIGHT_SEATS = 6;
        const WHEELCHAIR = new Set(["A01","A02","A17","A18"]);

        const seatGrid = document.getElementById("seat-grid");
        const statusText = document.getElementById("status-text");
        const toggleSeatNumber = document.getElementById("toggle-seat-number");
        const activityFeed = document.getElementById("activity-feed");
        const zoomRange = document.getElementById("zoom-range");
        const zoomInBtn = document.getElementById("zoom-in");
        const zoomOutBtn = document.getElementById("zoom-out");
        const rowLabelsLeft = document.getElementById("row-labels-left");
        const rowLabelsRight = document.getElementById("row-labels-right");
        const paymentButton = document.getElementById("confirm-btn");
        const paymentHint = document.getElementById("payment-hint");
        const paymentModal = document.getElementById("payment-modal");
        const paymentForm = document.getElementById("payment-form");
        const seatSummary = document.getElementById("seat-summary");
        const submitPaymentBtn = document.getElementById("submit-payment-btn");
        const modalCloseButtons = paymentModal.querySelectorAll("[data-close-modal]");

        const randomToken = (typeof crypto !== "undefined" && crypto.randomUUID)
            ? crypto.randomUUID().slice(0, 6)
            : Math.random().toString(36).slice(2, 8);
        const USER_ID = "USR-" + randomToken.toUpperCase();
        document.getElementById("user-display").innerText = USER_ID;

        const seatElements = new Map();
        const seatState = new Map();
        const selectedSeats = new Set();
        let socket = null;

        function updatePaymentActionState(){
            const hasSelection = selectedSeats.size > 0;
            paymentButton.disabled = !hasSelection;
            const seats = Array.from(selectedSeats).sort();
            if(hasSelection){
                const list = seats.join(", ");
                paymentHint.textContent = `Selecionado(s): ${list}`;
                seatSummary.textContent = `Você está confirmando ${seats.length} assento(s): ${list}`;
            }else{
                paymentHint.textContent = "Selecione ao menos uma poltrona.";
                seatSummary.textContent = "Selecione ao menos uma poltrona.";
            }
        }

        function pad(num){
            return String(num).padStart(2,"0");
        }

        function createSeat(row, number){
            const seatId = row + pad(number);
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "seat available";
            btn.dataset.seatId = seatId;
            btn.dataset.label = seatId;
            if(WHEELCHAIR.has(seatId)){
                btn.classList.add("wheelchair");
            }
            btn.addEventListener("click", () => handleSeatClick(seatId));
            seatElements.set(seatId, btn);
            seatState.set(seatId, "available");
            return btn;
        }

        function buildRow(row){
            const rowEl = document.createElement("div");
            rowEl.className = "seat-row";
            
            const leftGroup = document.createElement("div");
            leftGroup.className = "seat-group left";
            for(let i=1;i<=LEFT_SEATS;i++){
                leftGroup.appendChild(createSeat(row, i));
            }

            const walkway = document.createElement("div");
            walkway.className = "walkway";

            const rightGroup = document.createElement("div");
            rightGroup.className = "seat-group right";
            for(let i=LEFT_SEATS+1;i<=LEFT_SEATS+RIGHT_SEATS;i++){
                rightGroup.appendChild(createSeat(row, i));
            }

            rowEl.append(leftGroup, walkway, rightGroup);
            return rowEl;
        }

        function buildSeatMap(){
            ROWS.forEach(row => {
                const labelLeft = document.createElement("span");
                labelLeft.textContent = row;
                rowLabelsLeft.appendChild(labelLeft);

                const labelRight = document.createElement("span");
                labelRight.textContent = row;
                rowLabelsRight.appendChild(labelRight);

                seatGrid.appendChild(buildRow(row));
            });
        }

        function updateSeatState(seatId, state, toneMessage){
            const element = seatElements.get(seatId);
            if(!element) return;
            element.classList.remove("available","selected","blocked","reserved","pending");
            element.classList.add(state);
            const lockStates = ["selected","blocked","reserved","pending"];
            element.disabled = lockStates.includes(state);
            seatState.set(seatId, state);
            if(state === "selected"){
                selectedSeats.add(seatId);
            }else{
                selectedSeats.delete(seatId);
            }
            updatePaymentActionState();
            if(toneMessage){
                setStatus(toneMessage.text, toneMessage.tone);
            }
        }

        function setStatus(message, tone="info"){
            statusText.textContent = message;
            statusText.dataset.tone = tone;
        }

        function pushActivity(message){
            const li = document.createElement("li");
            const timestamp = new Date().toLocaleTimeString("pt-BR",{hour12:false,hour:"2-digit",minute:"2-digit"});
            li.textContent = `[${timestamp}] ${message}`;
            activityFeed.prepend(li);
            if(activityFeed.children.length > 3){
                activityFeed.removeChild(activityFeed.lastChild);
            }
        }

        function openPaymentModal(){
            if(paymentButton.disabled) return;
            paymentModal.classList.add("visible");
        }

        function closePaymentModal(){
            paymentModal.classList.remove("visible");
            paymentForm.reset();
            submitPaymentBtn.disabled = false;
        }

        function handlePaymentSubmit(event){
            event.preventDefault();
            if(selectedSeats.size === 0){
                setStatus("Selecione ao menos uma poltrona para confirmar.", "error");
                return;
            }
            if(!socket || socket.readyState !== WebSocket.OPEN){
                setStatus("Sem conexão com o servidor.", "error");
                return;
            }
            submitPaymentBtn.disabled = true;
            const formData = new FormData(paymentForm);
            const payload = {
                nomeCompleto: (formData.get("nomeCompleto") || "").trim(),
                cpf: (formData.get("cpf") || "").trim(),
                email: (formData.get("email") || "").trim()
            };
            socket.send(JSON.stringify({
                acao:"confirmar_pagamento",
                sessao:SESSION_ID,
                assentos:Array.from(selectedSeats),
                usuario_id:USER_ID,
                pagamento:payload
            }));
            setStatus("Processando pagamento...", "info");
        }

        function handlePaymentResponse(data){
            submitPaymentBtn.disabled = false;
            const confirmed = data.assentos_confirmados || [];
            const failed = data.assentos_falha || [];
            if((data.status === "ok" || data.status === "parcial") && confirmed.length){
                closePaymentModal();
                pushActivity(`Pagamento confirmado para ${confirmed.join(", ")}.`);
                setStatus(data.mensagem, data.status === "ok" ? "success" : "info");
            }else if(data.status === "erro"){
                setStatus(data.mensagem || "Não foi possível confirmar o pagamento.", "error");
            }

            confirmed.forEach(seat => selectedSeats.delete(seat));
            updatePaymentActionState();

            if(failed.length){
                pushActivity(`Falha ao confirmar: ${failed.join(", ")}.`);
            }
        }

        paymentButton.addEventListener("click", openPaymentModal);
        modalCloseButtons.forEach(btn => btn.addEventListener("click", closePaymentModal));
        paymentModal.addEventListener("click", (event) => {
            if(event.target === paymentModal){
                closePaymentModal();
            }
        });
        paymentForm.addEventListener("submit", handlePaymentSubmit);

        function handleSeatClick(seatId){
            const current = seatState.get(seatId);
            if(["blocked","reserved","selected","pending"].includes(current)){
                setStatus(`Assento ${seatId} indisponível no momento.`, "error");
                return;
            }
            if(!socket || socket.readyState !== WebSocket.OPEN){
                setStatus("Sem conexão com o servidor.", "error");
                return;
            }
            const element = seatElements.get(seatId);
            element.classList.add("pending");
            element.disabled = true;
            seatState.set(seatId, "pending");
            setStatus(`Solicitando bloqueio da poltrona ${seatId}...`, "info");
            socket.send(JSON.stringify({
                acao:"bloquear",
                sessao:SESSION_ID,
                assento:seatId,
                usuario_id:USER_ID
            }));
        }

        function connectWebSocket(){
            socket = new WebSocket(WS_URL);
            socket.onopen = () => {
                setStatus("Conectado. Escolha seu assento.", "success");
            };
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if(data.evento){
                    handleBroadcast(data);
                }else if(data.status){
                    handleResponse(data);
                }
            };
            socket.onerror = () => {
                setStatus("Erro na conexão. Tentando novamente...", "error");
            };
            socket.onclose = () => {
                setStatus("Conexão perdida. Reconnecting...", "error");
                setTimeout(connectWebSocket, 1500);
            };
        }

        function handleResponse(data){
            if(data.tipo === "confirmacao_pagamento"){
                handlePaymentResponse(data);
                return;
            }
            if(data.assento){
                const element = seatElements.get(data.assento);
                if(element){
                    element.classList.remove("pending");
                }
            }
            if(data.status === "erro"){
                if(data.assento){
                    updateSeatState(data.assento, "available");
                }
                setStatus(data.mensagem, "error");
            }else if(data.status){
                setStatus(data.mensagem, "success");
            }
        }

        function handleBroadcast(data){
            const seatId = data.assento;
            switch(data.evento){
                case "assento_bloqueado":
                    if(data.usuario_bloqueador === USER_ID){
                        updateSeatState(seatId, "selected", {text:`${seatId} bloqueado para você.`, tone:"success"});
                        pushActivity(`Você bloqueou ${seatId}.`);
                    }else{
                        updateSeatState(seatId, "blocked", {text:`${seatId} bloqueado por outro usuário.`, tone:"info"});
                        pushActivity(`${seatId} bloqueado por ${data.usuario_bloqueador}.`);
                    }
                    break;
                case "assento_liberado":
                    updateSeatState(seatId, "available", {text:`${seatId} liberado (${data.motivo || "livre"}).`, tone:"success"});
                    pushActivity(`${seatId} liberado.`);
                    break;
                case "assento_reservado":
                    updateSeatState(seatId, "reserved", {text:`${seatId} reservado permanentemente.`, tone:"info"});
                    pushActivity(`${seatId} reservado.`);
                    break;
                default:
                    break;
            }
        }

        toggleSeatNumber.addEventListener("change", (event) => {
            seatGrid.classList.toggle("show-labels", event.target.checked);
        });

        function setZoom(value){
            zoomRange.value = value;
            seatGrid.style.transform = `scale(${value/100})`;
        }
        zoomRange.addEventListener("input", e => setZoom(e.target.value));
        zoomInBtn.addEventListener("click", () => {
            const value = Math.min(130, Number(zoomRange.value) + 5);
            setZoom(value);
        });
        zoomOutBtn.addEventListener("click", () => {
            const value = Math.max(80, Number(zoomRange.value) - 5);
            setZoom(value);
        });

        buildSeatMap();
        updatePaymentActionState();
        setZoom(100);
        connectWebSocket();
    </script>
</body>
</html>
"""

RESERVAS_FILE = Path("reservas_confirmadas.json")
reservas_lock = Lock()
seat_snapshot_service = SeatStateService()
email_service = EmailService()
DEFAULT_SESSAO = "S001"


def append_confirmed_reservation(entry: dict) -> None:
    """Acrescenta uma reserva confirmada no arquivo JSON local."""
    with reservas_lock:
        if RESERVAS_FILE.exists():
            try:
                data = json.loads(RESERVAS_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = []
        else:
            data = []
        data.append(entry)
        RESERVAS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )


async def send_initial_state(websocket: WebSocket, sessao_id: str) -> None:
    """Envia o estado atual dos assentos já bloqueados/reservados para o cliente recém-conectado."""
    estados = seat_snapshot_service.listar_estado_sessao(sessao_id)
    if not estados:
        return

    for assento_num, valor in estados.items():
        if valor == "RESERVADO":
            payload = {
                "evento": "assento_reservado",
                "assento": assento_num
            }
        else:
            payload = {
                "evento": "assento_bloqueado",
                "assento": assento_num,
                "usuario_bloqueador": valor
            }
        await websocket.send_text(json.dumps(payload))


# Configuração
logging.basicConfig(level=logging.INFO, format='%(asctime)s - WebSocket - %(levelname)s - %(message)s')
app = FastAPI()

active_connections: list[WebSocket] = []

# --- Conexão gRPC com o Backend (Seu Booking Service) ---
# Importe os stubs gRPC (garanta que cinema_pb2 foi gerado)
import cinema_pb2
import cinema_pb2_grpc
GRPC_HOST = os.getenv('GRPC_HOST', 'localhost')
GRPC_HOST_PORT = f"{GRPC_HOST}:50051"
channel = grpc.insecure_channel(GRPC_HOST_PORT)
grpc_stub = cinema_pb2_grpc.ReservaStub(channel)


# --- Funções de Broadcast ---

async def broadcast(message: dict):
    """Envia uma mensagem para todos os clientes WebSocket conectados."""
    msg_json = json.dumps(message)
    # Cria uma lista de tarefas para enviar a mensagem a todos os clientes
    send_tasks = [conn.send_text(msg_json) for conn in active_connections]
    # Espera que todas as mensagens sejam enviadas
    await asyncio.gather(*send_tasks)
    logging.info(f"Broadcast enviado para {len(active_connections)} clientes: {message['evento']}")


# --- Endpoint REST para o Redis Listener ---

@app.post("/notify_liberacao")
async def notify_liberacao(request: Request):
    """Recebe notificação do Redis Listener quando um bloqueio expira (timeout)."""
    data = await request.json()
    assento_num = data.get("assento")
    
    # Faz o broadcast para o frontend (assento volta a ser verde)
    await broadcast({
        "evento": "assento_liberado",
        "assento": assento_num,
        "motivo": "timeout"
    })
    return {"message": "Notification received and broadcasted"}


# --- Endpoint WebSocket (A Comunicação em Tempo Real) ---

@app.websocket("/ws/reserva")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logging.info(f"Novo cliente conectado. Total: {len(active_connections)}")
    sessao_param = websocket.query_params.get("sessao", DEFAULT_SESSAO)
    await send_initial_state(websocket, sessao_param)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            acao = message.get("acao")
            
            sessao = message.get('sessao', sessao_param or DEFAULT_SESSAO)
            usuario = message['usuario_id']

            # --- AÇÃO: BLOQUEAR ASSENTO (Usuário Clicou) ---
            if acao == "bloquear":
                assento_num = message['assento']
                assento_id = cinema_pb2.AssentoID(sessao_id=sessao, assento_num=assento_num)
                request_grpc = cinema_pb2.ReservaRequest(assento=assento_id, usuario_id=usuario)
                try:
                    # Chama o gRPC para tentar bloquear (adquirir o lock no Redis)
                    response = grpc_stub.ReservarAssento(request_grpc)
                    
                    if response.sucesso:
                        # Bloqueio SUCESSO: Faz o broadcast para todos os clientes
                        await broadcast({
                            "evento": "assento_bloqueado",
                            "assento": assento_num,
                            "usuario_bloqueador": usuario
                        })
                        # Retorna a confirmação apenas para o cliente que solicitou
                        await websocket.send_text(json.dumps({
                            "status": "ok",
                            "mensagem": f"Assento {assento_num} bloqueado temporariamente.",
                            "assento": assento_num
                        }))
                    else:
                        # Bloqueio FALHA: Retorna a falha apenas para o cliente que solicitou
                        await websocket.send_text(json.dumps({
                            "status": "erro",
                            "mensagem": response.mensagem,
                            "assento": assento_num
                        }))
                        
                except grpc.RpcError as e:
                    logging.error(f"Erro gRPC ao bloquear: {e}")
                    await websocket.send_text(json.dumps({
                        "status": "erro",
                        "mensagem": "Erro interno no servidor de reserva.",
                        "assento": assento_num
                    }))
            
            elif acao == "confirmar_pagamento":
                assentos_payload = message.get("assentos") or []
                pagamento = message.get("pagamento") or {}
                required_fields = ("nomeCompleto", "cpf", "email")

                if not assentos_payload or not all(pagamento.get(field) for field in required_fields):
                    await websocket.send_text(json.dumps({
                        "status": "erro",
                        "tipo": "confirmacao_pagamento",
                        "mensagem": "Informe nome completo, CPF, e-mail e ao menos um assento.",
                        "assentos_confirmados": [],
                        "assentos_falha": assentos_payload
                    }))
                    continue

                confirmados: list[str] = []
                falhas: list[str] = []

                for assento in assentos_payload:
                    assento_id = cinema_pb2.AssentoID(sessao_id=sessao, assento_num=assento)
                    request_confirm = cinema_pb2.ReservaRequest(assento=assento_id, usuario_id=usuario)
                    try:
                        response = grpc_stub.ConfirmarPagamento(request_confirm)
                    except grpc.RpcError as e:
                        logging.error(f"Erro gRPC ao confirmar pagamento: {e}")
                        falhas.append(assento)
                        continue

                    if response.sucesso:
                        confirmados.append(assento)
                        await broadcast({
                            "evento": "assento_reservado",
                            "assento": assento,
                            "usuario_bloqueador": usuario
                        })
                    else:
                        falhas.append(assento)

                if confirmados:
                    append_confirmed_reservation({
                        "sessao_id": sessao,
                        "assentos": confirmados,
                        "usuario_id": usuario,
                        "nome_completo": pagamento["nomeCompleto"],
                        "cpf": pagamento["cpf"],
                        "email": pagamento["email"],
                        "timestamp": time.time()
                    })
                    email_service.send_confirmation(
                        nome=pagamento["nomeCompleto"],
                        email=pagamento["email"],
                        sessao=sessao,
                        assentos=confirmados
                    )

                if confirmados and not falhas:
                    status = "ok"
                    mensagem = "Pagamento confirmado! Seus assentos foram reservados."
                elif confirmados and falhas:
                    status = "parcial"
                    mensagem = "Alguns assentos foram confirmados. Revise os restantes."
                else:
                    status = "erro"
                    mensagem = "Não foi possível confirmar os assentos selecionados."

                await websocket.send_text(json.dumps({
                    "status": status,
                    "tipo": "confirmacao_pagamento",
                    "mensagem": mensagem,
                    "assentos_confirmados": confirmados,
                    "assentos_falha": falhas
                }))
            
            
    except Exception as e:
        logging.warning(f"Conexão fechada inesperadamente: {e}")
    finally:
        active_connections.remove(websocket)
        logging.info(f"Cliente desconectado. Total: {len(active_connections)}")


# --- Endpoint HTML para o Frontend Simples ---

@app.get("/", response_class=HTMLResponse)
async def get():
    return HTML_CONTENT