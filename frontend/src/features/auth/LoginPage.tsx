import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin } from '@/api/auth'
import { ApiError } from '@/api/client'

const schema = z.object({
  email: z.string().email('Email không hợp lệ'),
  password: z.string().min(8, 'Tối thiểu 8 ký tự'),
})

type LoginInput = z.infer<typeof schema>

export default function LoginPage() {
  const nav = useNavigate()
  const login = useLogin()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({ resolver: zodResolver(schema) })

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <form
        onSubmit={handleSubmit(async (v) => {
          try {
            await login.mutateAsync(v)
            nav('/dashboard')
          } catch {
            /* error rendered below via login.error */
          }
        })}
        className="w-[380px] border border-hairline bg-paper-2 p-8 space-y-5"
      >
        <h1 className="font-serif text-xl text-ink">Đăng nhập</h1>

        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-muted text-[11px] uppercase tracking-wide">
            Email
          </Label>
          <Input id="email" type="email" autoFocus {...register('email')} />
          {errors.email && <p className="text-warn text-xs">{errors.email.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password" className="text-muted text-[11px] uppercase tracking-wide">
            Mật khẩu
          </Label>
          <Input id="password" type="password" {...register('password')} />
          {errors.password && <p className="text-warn text-xs">{errors.password.message}</p>}
        </div>

        {login.error instanceof ApiError && (
          <p className="text-warn text-xs">
            {login.error.code === 'INVALID_CREDENTIALS'
              ? 'Email hoặc mật khẩu sai'
              : login.error.message}
          </p>
        )}

        <Button type="submit" disabled={login.isPending} className="w-full">
          {login.isPending ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>

        <p className="text-muted text-xs text-center">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-accent">
            Đăng ký
          </Link>
        </p>
      </form>
    </div>
  )
}
