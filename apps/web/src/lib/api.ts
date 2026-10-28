export type Me={id:string;email:string;role:string;locale:string};
export type Window={id:string;starts_at:string;ends_at:string;capacity:number;reserved:number;version:number};
export type Package={id:string;ordinal:number;retailer:string;carrier:string;destination_name:string;status:string;version:number};
export type Booking={id:string;reference:string;status:string;locale:string;pickup_address:Record<string,string>;preferred_at:string|null;subtotal_cents:number;tax_cents:number;total_cents:number;payment_status:string;version:number;packages:Package[]};
export type Evidence={id:string;package_id:string;kind:string;storage_key:string;checksum:string;status:string;captured_at:string};
export type Stop={id:string;booking_id:string;sequence:number;kind:string;planned_at:string;service_minutes:number;status:string};
export type Route={id:string;public_id:string;driver_id:string;service_date:string;status:string;version:number;plan:{hard_constraints_validated:boolean;[key:string]:unknown};published_at:string|null;stops:Stop[]};
export type Driver={id:string;name:string;email:string};
export type Quote={payment_method:string;subtotal_cents:number;tax_cents:number;total_cents:number};

const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function api<T>(path: string, user: string, init?: RequestInit): Promise<T> {
  const headers: Record<string,string> = {"Content-Type":"application/json",...(init?.headers as Record<string,string>|undefined)};
  if(process.env.NODE_ENV!=="production") headers["X-Returnet-Dev-User"]=user;
  else if(typeof window!=="undefined"&&localStorage.getItem("returnet.token")) headers.Authorization=`Bearer ${localStorage.getItem("returnet.token")}`;
  const response = await fetch(`${base}${path}`, {
    ...init,
    cache: "no-store",
    headers
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.error?.message ?? `Request failed (${response.status})`,response.status,body?.error?.code??`http.${response.status}`);
  }
  return response.json() as Promise<T>;
}

export class ApiError extends Error { constructor(message:string,public status:number,public code:string){super(message)} }
