import sys
import asyncio
import uvicorn
from app.config import HOST, PORT, ADMIN_PORT
from app.main import app

async def run_dual_servers():
    """
    Runs both the main DevOps Hub portal (port 8926) and the private
    Admin Portal (port 9256) concurrently in a single high-performance asyncio event loop.
    Both servers share the same memory space, ensuring instant cache synchronization.
    """
    config_main = uvicorn.Config(
        app,
        host=HOST,
        port=PORT,
        log_level="info",
        lifespan="on",
        access_log=True
    )
    
    config_admin = uvicorn.Config(
        app,
        host=HOST,
        port=ADMIN_PORT,
        log_level="info",
        lifespan="off",  # Main server manages startup/shutdown lifespan
        access_log=True
    )

    server_main = uvicorn.Server(config_main)
    server_admin = uvicorn.Server(config_admin)

    # Monitor shutdown signals across both servers
    async def monitor_shutdown():
        while not (server_main.should_exit or server_admin.should_exit):
            await asyncio.sleep(0.5)
        server_main.should_exit = True
        server_admin.should_exit = True

    try:
        await asyncio.gather(
            server_main.serve(),
            server_admin.serve(),
            monitor_shutdown()
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        server_main.should_exit = True
        server_admin.should_exit = True

def main():
    # If specific port argument is passed, run single server (backward compatibility)
    if "--single" in sys.argv or "--port" in sys.argv:
        port_to_use = PORT
        if "--port" in sys.argv:
            idx = sys.argv.index("--port")
            if idx + 1 < len(sys.argv):
                port_to_use = int(sys.argv[idx + 1])
        print(f">> Starting DevOps Hub single instance on port {port_to_use}...")
        uvicorn.run("app.main:app", host=HOST, port=port_to_use, reload=False)
        return

    print("=" * 70)
    print("DevOps Knowledge Portal & Interview Hub (Multi-Port Engine)")
    print("=" * 70)
    print(f"  * Public Web Portal  : http://{HOST}:{PORT}")
    print(f"  * Admin Private Hub  : http://{HOST}:{ADMIN_PORT}")
    print("=" * 70)

    try:
        asyncio.run(run_dual_servers())
    except (KeyboardInterrupt, SystemExit):
        print("\nDevOps Hub services shutdown gracefully.")

if __name__ == "__main__":
    main()
