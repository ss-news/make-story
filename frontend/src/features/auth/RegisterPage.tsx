import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useRegister } from '@/api/auth'
import { ApiError } from '@/api/client'

const schema = z.object({
  display_name: z.string().min(1, 'Bắt buộc'),
  email: z.string().email('Email không hợp lệ'),
  password: z.string().min(8, 'Tối thiểu 8 ký tự'),
})

type RegisterInput = z.infer<typeof schema>

function errorMessage(err: ApiError): string {
  switch (err.code) {
    case 'EMAIL_TAKEN':
      return 'Email đã được sử dụng'
    case 'REGISTRATION_DISABLED':
      return 'Đăng ký đang tạm khoá'
    default:
      return err.message
  }
}

export default function RegisterPage() {
  const nav = useNavigate()
  const reg = useRegister()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterInput>({ resolver: zodResolver(schema) })

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <form
        onSubmit={handleSubmit(async (v) => {
          try {
            await reg.mutateAsync(v)
            nav('/dashboard')
          } catch {
            /* error rendered below via reg.error */
          }
        })}
        className="w-[380px] border border-hairline bg-paper-2 p-8 space-y-5"
      >
        <h1 className="font-serif text-xl text-ink">Đăng ký</h1>

        <div className="space-y-1.5">
          <Label htmlFor="display_name" className="text-muted text-[11px] uppercase tracking-wide">
            Tên hiển thị
          </Label>
          <Input id="display_name" type="text" autoFocus {...register('display_name')} />
          {errors.display_name && (
            <p className="text-warn text-xs">{errors.display_name.message}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-muted text-[11px] uppercase tracking-wide">
            Email
          </Label>
          <Input id="email" type="email" {...register('email')} />
          {errors.email && <p className="text-warn text-xs">{errors.email.message}</p>}
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="password" className="text-muted text-[11px] uppercase tracking-wide">
            Mật khẩu
          </Label>
          <Input id="password" type="password" {...register('password')} />
          {errors.password && <p className="text-warn text-xs">{errors.password.message}</p>}
        </div>

        {reg.error instanceof ApiError && (
          <p className="text-warn text-xs">{errorMessage(reg.error)}</p>
        )}

        <Button type="submit" disabled={reg.isPending} className="w-full">
          {reg.isPending ? 'Đang đăng ký…' : 'Đăng ký'}
        </Button>

        <p className="text-muted text-xs text-center">
          Đã có tài khoản?{' '}
          <Link to="/login" className="text-accent">
            Đăng nhập
          </Link>
        </p>
      </form>
    </div>
  )
}
