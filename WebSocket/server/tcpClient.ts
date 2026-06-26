import net from 'node:net';

export interface ModbusTcpOptions {
  host: string;
  port: number;
  unitId?: number;
  timeoutMs?: number;
}

export class ModbusTcpClient {
  private socket: net.Socket | null = null;

  constructor(private readonly options: ModbusTcpOptions) {}

  isConfigured() {
    return Boolean(this.options.host && this.options.port);
  }

  async connect(): Promise<void> {
    if (this.socket) {
      return;
    }

    // TODO: 실제 Modbus TCP 프레임 헤더와 레지스터 매핑을 여기에 연결한다.
    this.socket = net.createConnection({
      host: this.options.host,
      port: this.options.port,
    });

    this.socket.setTimeout(this.options.timeoutMs ?? 3000);

    await new Promise<void>((resolve, reject) => {
      if (!this.socket) {
        reject(new Error('Socket not initialized'));
        return;
      }

      this.socket.once('connect', () => resolve());
      this.socket.once('error', (error) => reject(error));
      this.socket.once('timeout', () => reject(new Error('Modbus TCP connection timed out')));
    });
  }

  async disconnect(): Promise<void> {
    if (!this.socket) {
      return;
    }

    const socket = this.socket;
    this.socket = null;

    await new Promise<void>((resolve) => {
      socket.once('close', () => resolve());
      socket.destroy();
    });
  }

  async readHoldingRegisters(_address: number, _quantity: number): Promise<number[]> {
    // TODO: 실제 PLC 주소 테이블을 주입하고 바이트 순서를 표준화한다.
    throw new Error('Modbus read skeleton is not wired to a PLC yet.');
  }

  async writeSingleRegister(_address: number, _value: number): Promise<void> {
    // TODO: 실제 쓰기 프레임을 생성한 뒤 ACK/NAK를 처리한다.
    throw new Error('Modbus write skeleton is not wired to a PLC yet.');
  }
}
