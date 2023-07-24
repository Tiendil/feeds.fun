import {setIntervalAsync, clearIntervalAsync} from "set-interval-async";

export class Timer {
  _timer: any;
  _refresher: any;
  delay: number;

  constructor(refresher: any, delay: number) {
    this._timer = null;
    this._refresher = refresher;
    this.delay = delay;
  }

  async start() {
    await this._refresher();
    this._timer = setIntervalAsync(this._refresher, this.delay);
  }

  async stop() {
    if (this._timer != null) {
      await clearIntervalAsync(this._timer);
      this._timer = null;
    }
  }
}
