"use client";
import { useState, useEffect } from "react";

export default function AMEDashboard() {
  const [ames, setAmes] = useState([
    {
      id: 1,
      name: "AME Principal",
      status: "activo",
      lastSync: "hace 2 min",
      skills: 5,
      level: 1,
    },
    {
      id: 2,
      name: "AME Educativo",
      status: "activo",
      lastSync: "hace 5 min",
      skills: 3,
      level: 1,
    },
    {
      id: 3,
      name: "AME Productividad",
      status: "activo",
      lastSync: "hace 10 min",
      skills: 4,
      level: 1,
    },
  ]);
  const [offline, setOffline] = useState(
    typeof window !== "undefined" && !navigator.onLine,
  );

  useEffect(() => {
    const handleOnline = () => setOffline(false);
    const handleOffline = () => setOffline(true);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #080408 0%, #1a1a2e 100%)",
        color: "#F0F0F8",
        padding: "20px",
      }}
    >
      <div
        style={{
          marginBottom: "40px",
          paddingBottom: "20px",
          borderBottom: "2px solid #DC143C",
        }}
      >
        <h1 style={{ fontSize: "36px", margin: "0 0 10px 0" }}>
          AME Dashboard Activo
        </h1>
        {offline && (
          <div
            style={{
              marginTop: "15px",
              padding: "12px",
              background: "#FFD700",
              color: "#080408",
              borderRadius: "6px",
              fontWeight: "bold",
              display: "inline-block",
            }}
          >
            Modo offline - Datos sincronizados localmente
          </div>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: "20px",
          marginBottom: "40px",
        }}
      >
        {ames.map((ame) => (
          <div
            key={ame.id}
            onClick={() => (window.location.href = `/ame/${ame.id}`)}
            style={{
              background: "#1a1a2e",
              border: "2px solid #DC143C",
              borderRadius: "12px",
              padding: "25px",
              cursor: "pointer",
              transition: "all 0.3s ease",
              position: "relative",
              overflow: "hidden",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#FFD700";
              e.currentTarget.style.boxShadow = "0 0 20px rgba(255,215,0,0.3)";
              e.currentTarget.style.transform = "translateY(-5px)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#DC143C";
              e.currentTarget.style.boxShadow = "none";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <div style={{ position: "relative", zIndex: 1 }}>
              <h3
                style={{
                  margin: "0 0 15px 0",
                  fontSize: "20px",
                  fontWeight: "bold",
                }}
              >
                {ame.name}
              </h3>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "15px",
                  marginBottom: "15px",
                }}
              >
                <div>
                  <p
                    style={{
                      margin: "0 0 5px 0",
                      opacity: 0.7,
                      fontSize: "12px",
                    }}
                  >
                    Estado
                  </p>
                  <p style={{ margin: "0", fontWeight: "bold" }}>
                    <span style={{ color: "#FFD700" }}>Activo</span>
                  </p>
                </div>
                <div>
                  <p
                    style={{
                      margin: "0 0 5px 0",
                      opacity: 0.7,
                      fontSize: "12px",
                    }}
                  >
                    Level
                  </p>
                  <p style={{ margin: "0", fontWeight: "bold" }}>
                    Lv. {ame.level} ({ame.skills} skills)
                  </p>
                </div>
              </div>
              <p
                style={{
                  margin: "0",
                  opacity: 0.6,
                  fontSize: "12px",
                  borderTop: "1px solid rgba(255,215,0,0.2)",
                  paddingTop: "10px",
                }}
              >
                {ame.lastSync}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "15px",
          marginTop: "30px",
        }}
      >
        <button
          onClick={() => alert("Crear nuevo AME - Prximamente")}
          style={{
            background: "linear-gradient(135deg, #DC143C, #FF1744)",
            color: "#F0F0F8",
            border: "none",
            padding: "15px 25px",
            fontSize: "16px",
            fontWeight: "bold",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          + Crear AME
        </button>
        <button
          onClick={() => (window.location.href = "/ame/evolution")}
          style={{
            background: "rgba(255,215,0,0.1)",
            border: "2px solid #FFD700",
            color: "#FFD700",
            padding: "15px 25px",
            fontSize: "16px",
            fontWeight: "bold",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Evolución
        </button>
        <button
          onClick={() => alert("Comunidad - Próximamente")}
          style={{
            background: "rgba(220,20,60,0.1)",
            border: "2px solid #DC143C",
            color: "#F0F0F8",
            padding: "15px 25px",
            fontSize: "16px",
            fontWeight: "bold",
            borderRadius: "8px",
            cursor: "pointer",
          }}
        >
          Comunidad
        </button>
      </div>
    </div>
  );
}
