type Props = {};

export default function LiveBrowser(_props: Props) {
    return (
        <div className="live-browser">
            <div className="live-browser-header">
                <span className="live-browser-title">Live Browser</span>
                <span className="live-browser-status" aria-label="Estado del stream">
                    desconectado
                </span>
            </div>
            <div className="live-browser-viewport">
                <img
                    alt="Vista del navegador remoto"
                    className="live-browser-frame"
                    style={{ display: "none" }}
                />
                <div className="live-browser-placeholder">Stream no iniciado</div>
            </div>
        </div>
    );
}
