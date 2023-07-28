import _ from "lodash";

export function timeSince(date: Date) {
  const now = new Date();

  const secondsPast = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (secondsPast < 60) {
    return "<min";
  }

  const minutesPast = Math.floor(secondsPast / 60);

  if (minutesPast < 60) {
    return `${minutesPast}min`;
  }

  const hoursPast = Math.floor(minutesPast / 60);

  if (hoursPast < 24) {
    return `${hoursPast}h`;
  }

  const daysPast = Math.floor(hoursPast / 24);

  if (daysPast < 30) {
    return `${daysPast}d`;
  }

  const monthsPast = Math.floor(daysPast / 30);

  if (monthsPast < 12) {
    return `${monthsPast}m`;
  }

  const yearsPast = Math.floor(monthsPast / 12);

  return `${yearsPast}y`;
}
